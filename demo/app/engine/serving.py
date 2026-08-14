"""Serving-mode index over experiments/chrono.py.

night_lab.build_context() is written for one benchmark instance: it rebuilds
tree, blobs, BM25 and both graph layers on every call (~6 s median). Serving
needs the same computation split in two:

  RepoIndex        built once per revision (seconds)
  localize/impact  per query (milliseconds), issue-dependent parts only

The candidate recipe itself is NOT reimplemented here: `_fuse` reproduces
night_lab.rrf_final(k=40, exclude=("gr",)) list for list, and
demo/tests/test_parity.py asserts the two agree element by element on real
benchmark instances, and that the baskets equal the ones shipped in
data/rerank_final_lite.jsonl.
"""
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..config import settings  # noqa: F401  (puts experiments/ on sys.path)
from . import evidence as ev

import chrono
import night_lab as nl

LAM = nl.LAM            # 1/90 per day
ALPHA = 0.25            # static/temporal mix
RRF_K = 40
EXCLUDE = ("gr",)
TOP = nl.TOP            # 100
SEED_TOP = 10           # seed files used for evidence (as in prepare_rerank50)

FUSE_LABELS = {
    "bm": "BM25",
    "gr": "identifier search",
    "ppr_bm": "propagation (BM25 seed)",
    "ppr_gr": "propagation (identifier seed)",
    "rec": "recency prior",
    "path": "path tokens",
    "expl": "paths quoted in issue",
}


class Timer:
    """Collects per-stage wall time in ms."""

    def __init__(self):
        self.ms = {}

    def __call__(self, name):
        return _Span(self, name)


class _Span:
    def __init__(self, timer, name):
        self.timer, self.name = timer, name

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.timer.ms[self.name] = round(
            (time.perf_counter() - self.t0) * 1000, 1)
        return False


# ------------------------------------------------------------------ mining

def mine_pairs(history, ancestors, base_ts, file_set, lam=LAM):
    """One pass over history -> {(a,b): [raw_count, decayed_weight, last_ts]}.

    Equivalent to calling chrono.temporal_edges twice (lam and 0.0) plus a
    last-seen pass; tests assert the equivalence.
    """
    pairs = {}
    for sha, ts, files in history:
        if sha not in ancestors:
            continue
        alive = [f for f in files if f in file_set]
        if len(alive) < 2:
            continue
        w = math.exp(-lam * max(0.0, (base_ts - ts) / 86400.0)) if lam > 0 \
            else 1.0
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                key = (alive[i], alive[j]) if alive[i] < alive[j] \
                    else (alive[j], alive[i])
                rec = pairs.get(key)
                if rec is None:
                    pairs[key] = [1, w, ts]
                else:
                    rec[0] += 1
                    rec[1] += w
                    if ts > rec[2]:
                        rec[2] = ts
    return pairs


# ------------------------------------------------------------------ index

@dataclass
class RepoIndex:
    repo: str                       # owner/name
    rev: str                        # resolved commit sha
    repo_dir: Path
    base_ts: int
    files: dict                     # path -> blob sha (insertion order = ls-tree)
    py_files: dict
    py_paths: list
    py_idx: dict
    bm25: object
    blob_cache: object
    s_edges: dict
    pairs: dict                     # (a,b) -> [raw, decayed, last_ts]
    rows_s: dict
    rows_t: dict
    recency: dict
    freq: Counter
    history: list
    ancestors: set
    stats: dict = field(default_factory=dict)

    # ---- derived, built once ----------------------------------------
    def __post_init__(self):
        self.t_raw = {k: v[0] for k, v in self.pairs.items()}
        self.last_seen = {k: v[2] for k, v in self.pairs.items()}
        self.adj = defaultdict(dict)
        self.involvement = Counter()
        for (a, b), rec in self.pairs.items():
            self.adj[a][b] = rec[0]
            self.adj[b][a] = rec[0]
            self.involvement[a] += rec[0]
            self.involvement[b] += rec[0]
        self.imports_adj = defaultdict(set)
        for a, b in self.s_edges:
            self.imports_adj[a].add(b)
            self.imports_adj[b].add(a)
        # mixing the two layers costs ~80 ms at django scale; queries reuse it
        self._rows_cache = {}

    def mixed_rows(self, alpha):
        """chrono.mix_rows(rows_s, rows_t, alpha), memoized per alpha."""
        rows = self._rows_cache.get(alpha)
        if rows is None:
            rows = chrono.mix_rows(self.rows_s, self.rows_t, alpha, self.n_py)
            self._rows_cache[alpha] = rows
        return rows

    @property
    def id(self):
        return f"{self.repo.replace('/', '__')}@{self.rev[:12]}"

    @property
    def n_py(self):
        return len(self.py_paths)

    # ---- ctx adapter -------------------------------------------------
    def base_ctx(self):
        """The revision-dependent half of night_lab's ctx."""
        return {
            "files": self.files,
            "py_idx": self.py_idx,
            "n_py": self.n_py,
            "all_paths_list": list(self.files),
            "bm25": self.bm25,
            "recency": self.recency,
            "freq": self.freq,
            "rows_s": self.rows_s,
            "rows_t": self.rows_t,
        }

    def issue_ctx(self, issue, timer=None):
        """The issue-dependent half: BM25/grep/path/explicit seeds.

        Mirrors night_lab.build_context() exactly for the lists the final
        recipe consumes (rm3 is not one of them and is skipped).
        """
        timer = timer or Timer()
        ctx = self.base_ctx()
        with timer("bm25"):
            ctx["seed_bm"] = self.bm25.query(chrono.tokenize(issue, cap=3000),
                                             top=200)
        with timer("grep"):
            idents = chrono.issue_identifiers(issue)
            ctx["seed_gr"] = chrono.grep_scores(idents, self.files,
                                                self.blob_cache, top=200)
        with timer("paths"):
            explicit, seen = [], set()
            for m in nl._PATH_RE.finditer(issue[:6000]):
                cand = m.group(0).lstrip("./")
                for p in self.files:
                    if (p == cand or p.endswith("/" + cand)) and p not in seen:
                        explicit.append(p)
                        seen.add(p)
            ctx["explicit_paths"] = explicit[:10]

            q_toks = set(chrono.tokenize(issue, cap=1500))
            path_scores = []
            for p in self.files:
                toks = set(chrono.subtokens(
                    p.replace("/", "_").replace(".", "_")))
                inter = len(q_toks & toks)
                if inter:
                    path_scores.append((p, inter / (1 + math.log(1 + len(toks)))))
            ctx["seed_path"] = sorted(path_scores, key=lambda kv: -kv[1])[:60]
        return ctx, timer

    # ---- queries -----------------------------------------------------
    def localize(self, issue, depth=50):
        """issue -> BM25 / candidates / provenance / evidence."""
        timer = Timer()
        ctx, timer = self.issue_ctx(issue, timer)
        with timer("propagate"):
            rows = self.mixed_rows(ALPHA)      # == night_lab.mix(ctx, 0.25)
            hyb_bm = chrono.hybrid_rank(ctx["seed_bm"], rows, self.py_idx,
                                        self.n_py, ctx["all_paths_list"],
                                        top=100, return_scores=True)
            hyb_gr = chrono.hybrid_rank(ctx["seed_gr"], rows, self.py_idx,
                                        self.n_py, ctx["all_paths_list"],
                                        top=100)
        with timer("fuse"):
            ranked, score, sources = _fuse(
                ctx, [p for p, _ in hyb_bm], hyb_gr, k=RRF_K, exclude=EXCLUDE)
        with timer("evidence"):
            ppr_norm = _ppr_scores(ctx, rows, self.py_idx, self.n_py)
            seed_top = [p for p, _ in ctx["seed_bm"][:SEED_TOP]]
            cands = []
            for rank, p in enumerate(ranked[:depth], 1):
                chips = ev.chips(seed_top, p, self.s_edges, self.t_raw,
                                 ppr_norm.get(p, 0.0), self.last_seen)
                cands.append({
                    "file": p, "rank": rank,
                    "rrf": round(score[p], 5),
                    "sources": [{"list": n, "label": FUSE_LABELS[n],
                                 "rank": r, "contrib": round(c, 5)}
                                for n, r, c in sources[p]],
                    "evidence": chips,
                    "evidence_text": ev.render(chips),
                })
        return {
            "bm25": [p for p, _ in ctx["seed_bm"][:depth]],
            "candidates": cands,
            "candidate_paths": ranked,
            "timings_ms": timer.ms,
            "n_candidates": len(ranked),
            "seed_files": seed_top,
        }

    def impact(self, seed, k=20):
        """One file -> the files likely to change with it (four methods)."""
        if seed not in self.py_files:
            raise KeyError(seed)
        timer = Timer()
        seed_list = [(seed, 1.0)]
        out = {}
        with timer("rose"):
            nbrs = self.adj.get(seed, {})
            out["rose"] = [(p, float(nbrs[p])) for p in
                           sorted(nbrs, key=nbrs.get, reverse=True)[:k]]
        with timer("freq"):
            out["freq"] = [(p, float(c)) for p, c in
                           self.freq.most_common(k + 1) if p != seed][:k]
        for name, alpha in (("static_ppr", 1.0), ("temporal_ppr", 0.0),
                            ("hybrid_a25", ALPHA)):
            with timer(name):
                rows = self.mixed_rows(alpha)
                ranked = chrono.hybrid_rank(seed_list, rows, self.py_idx,
                                            self.n_py, self.py_paths,
                                            beta=0.0, top=k + 1,
                                            return_scores=True)
                out[name] = [(p, s) for p, s in ranked if p != seed][:k]
        methods = {}
        for name, rows_ in out.items():
            methods[name] = [{
                "file": p, "score": round(s, 5),
                "evidence": self.pair_evidence(seed, p),
            } for p, s in rows_]
        return {"seed": seed, "methods": methods, "timings_ms": timer.ms}

    def pair_evidence(self, a, b):
        chips = []
        key = (a, b) if a < b else (b, a)
        rec = self.pairs.get(key)
        if rec:
            chips.append({"kind": "cochange", "with": a, "count": int(rec[0]),
                          "last": ev.month(rec[2]),
                          "decayed": round(rec[1], 3)})
        if key in self.s_edges:
            chips.append({"kind": "import", "with": a})
        if not rec:
            chips += ev.bridge(a, b, self.adj, exclude=(a, b))
        return chips

    # ---- graph view --------------------------------------------------
    def subgraph(self, focus=None, limit=140, min_count=2, max_edges=600,
                 ts_cap=400):
        """Nodes+edges for the visualization, with per-edge commit stamps.

        Sending the actual timestamps (most recent `ts_cap` per edge) lets
        the client recompute the decayed weight for any cutoff with the same
        formula as chrono.temporal_edges, exactly and without a round trip.
        """
        if focus and focus in self.py_files:
            nodes = _neighbourhood(self.adj, self.imports_adj, focus, limit)
        else:
            nodes = [p for p, _ in self.involvement.most_common(limit)]
            if not nodes:
                nodes = self.py_paths[:limit]
        nset = set(nodes)
        temporal = []
        for (a, b), rec in self.pairs.items():
            if a in nset and b in nset and rec[0] >= min_count:
                temporal.append({"a": a, "b": b, "count": rec[0],
                                 "decayed": round(rec[1], 4),
                                 "last": rec[2]})
        temporal.sort(key=lambda e: -e["count"])
        temporal = temporal[:max_edges]
        stamps = self._edge_stamps({(e["a"], e["b"]) for e in temporal},
                                   nset, ts_cap)
        for e in temporal:
            e["ts"] = stamps.get((e["a"], e["b"]), [])
        static = [{"a": a, "b": b} for (a, b) in self.s_edges
                  if a in nset and b in nset]
        mx = max((self.involvement.get(p, 0) for p in nodes), default=1) or 1
        return {
            "nodes": [{"file": p,
                       "dir": p.rsplit("/", 1)[0] if "/" in p else "",
                       "w": round(self.involvement.get(p, 0) / mx, 4),
                       "changes": int(self.freq.get(p, 0)),
                       "imports": len(self.imports_adj.get(p, ()))}
                      for p in nodes],
            "static": static,
            "temporal": temporal,
            "focus": focus,
            "lambda_per_day": LAM,
            "base_ts": self.base_ts,
            "span": [min((c[2] for c in self.pairs.values()), default=0),
                     self.base_ts],
        }

    def _edge_stamps(self, wanted, nset, cap):
        out = defaultdict(list)
        if not wanted:
            return out
        for sha, ts, files in self.history:
            if sha not in self.ancestors:
                continue
            alive = [f for f in files if f in nset]
            if len(alive) < 2:
                continue
            for i in range(len(alive)):
                for j in range(i + 1, len(alive)):
                    key = (alive[i], alive[j]) if alive[i] < alive[j] \
                        else (alive[j], alive[i])
                    if key in wanted:
                        out[key].append(ts)
        for k in out:
            out[k] = sorted(out[k])[-cap:]
        return out

    def search(self, q, limit=30):
        q = q.lower()
        hits = [p for p in self.py_files if q in p.lower()]
        hits.sort(key=lambda p: (-self.involvement.get(p, 0), len(p)))
        return hits[:limit]


def _neighbourhood(adj, imports_adj, focus, limit):
    """focus + strongest co-change neighbours + import neighbours, then a
    second hop until `limit` nodes are collected."""
    nodes = [focus]
    seen = {focus}
    frontier = [focus]
    while frontier and len(nodes) < limit:
        nxt = []
        for f in frontier:
            nbrs = sorted(adj.get(f, {}), key=adj[f].get, reverse=True)
            for p in list(imports_adj.get(f, ()))[:10] + nbrs[:20]:
                if p not in seen:
                    seen.add(p)
                    nodes.append(p)
                    nxt.append(p)
                    if len(nodes) >= limit:
                        return nodes
        frontier = nxt
    return nodes


# ------------------------------------------------------------------ fusion

def _fuse(ctx, ppr_bm, ppr_gr, k=RRF_K, exclude=EXCLUDE):
    """night_lab.rrf_final's fusion, with per-candidate provenance kept.

    Same seven lists, same depths (100/100/100/100/100/60/all), same weights
    and the same demote()+truncation, so the returned ranking is identical to
    rrf_final's (asserted in tests).
    """
    lists = [
        ("bm", 1.0, [p for p, _ in ctx["seed_bm"][:100]]),
        ("gr", 1.0, [p for p, _ in ctx["seed_gr"][:100]]),
        ("ppr_bm", 1.0, ppr_bm[:100]),
        ("ppr_gr", 1.0, ppr_gr[:100]),
        ("rec", 1.0, [p for p, _ in sorted(ctx["recency"].items(),
                                           key=lambda kv: -kv[1])[:100]]),
        ("path", 1.0, [p for p, _ in ctx["seed_path"][:60]]),
        ("expl", 1.0, ctx["explicit_paths"]),
    ]
    score = defaultdict(float)
    sources = defaultdict(list)
    for name, w, lst in lists:
        if name in exclude:
            continue
        for r, p in enumerate(lst):
            c = w / (k + r + 1)
            score[p] += c
            sources[p].append((name, r + 1, c))
    ranked = [p for p, _ in sorted(score.items(), key=lambda kv: -kv[1])]
    return nl.demote(ranked[:TOP * 2])[:TOP], score, sources


def _ppr_scores(ctx, rows, py_idx, n_py):
    """Normalized propagation score per file (evidence chip 'graph score'),
    same construction as prepare_rerank50."""
    seed_list = ctx["seed_bm"]
    seed_vec = [0.0] * n_py
    tot = sum(s for _, s in seed_list[:20]) or 1.0
    for p, s in seed_list[:20]:
        i = py_idx.get(p)
        if i is not None:
            seed_vec[i] += s / tot
    pv = chrono.ppr(rows, seed_vec, n_py)
    pmax = max(pv) or 1.0
    return {p: pv[i] / pmax for p, i in py_idx.items() if pv[i] > 0}


# ------------------------------------------------------------------ build

def build_index(repo, repo_dir, rev="HEAD", progress=None, history=None):
    """Build a RepoIndex at `rev`. progress(stage, status, **info)."""
    def emit(stage, status="done", **info):
        if progress:
            progress(stage, status, **info)

    repo_dir = Path(repo_dir)
    stats, t_all = {}, time.perf_counter()

    t0 = time.perf_counter()
    sha = chrono.git(repo_dir, "rev-parse", rev).strip()
    ancestors = chrono.ancestor_set(repo_dir, sha)
    base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                             sha).strip())
    stats["resolve_ms"] = _ms(t0)
    emit("resolve", rev=sha, commits_in_ancestry=len(ancestors))

    t0 = time.perf_counter()
    if history is None:
        cache = settings.cache_dir / f"{repo.replace('/', '__')}_log.pkl"
        history = chrono.mine_history(repo_dir, cache)
    stats["history_ms"] = _ms(t0)
    stats["commits_mined"] = len(history)
    emit("history", commits=len(history), ms=stats["history_ms"])

    t0 = time.perf_counter()
    files = chrono.tree_at(repo_dir, sha)
    py_files = {p: s for p, s in files.items() if p.endswith(".py")}
    stats["tree_ms"] = _ms(t0)
    stats["files"] = len(files)
    stats["py_files"] = len(py_files)
    emit("tree", files=len(files), py_files=len(py_files))

    t0 = time.perf_counter()
    bc = chrono.BlobCache(repo_dir)
    paths = list(files)
    for i in range(0, len(paths), 400):
        bc.load_missing({p: files[p] for p in paths[i:i + 400]})
        emit("blobs", "progress", done=min(i + 400, len(paths)),
             total=len(paths))
    stats["blobs_ms"] = _ms(t0)
    emit("blobs", ms=stats["blobs_ms"], blobs=len(bc.tokens))

    t0 = time.perf_counter()
    docs = {p: bc.tokens[s] for p, s in files.items() if s in bc.tokens}
    bm25 = chrono.BM25(docs)
    stats["bm25_ms"] = _ms(t0)
    emit("bm25", docs=len(docs), terms=len(bm25.idf))

    t0 = time.perf_counter()
    s_edges = chrono.static_edges(files, bc, repo_dir)
    bc.imports.clear()
    stats["imports_ms"] = _ms(t0)
    stats["import_edges"] = len(s_edges)
    emit("imports", edges=len(s_edges), ms=stats["imports_ms"])

    t0 = time.perf_counter()
    pairs = mine_pairs(history, ancestors, base_ts, set(py_files), LAM)
    recency = defaultdict(float)
    freq = Counter()
    for csha, ts, fs in history:
        if csha not in ancestors:
            continue
        w = math.exp(-LAM * max(0.0, (base_ts - ts) / 86400.0))
        for f in fs:
            if f in files:
                recency[f] += w
                freq[f] += 1
    stats["temporal_ms"] = _ms(t0)
    stats["cochange_edges"] = len(pairs)
    emit("temporal", edges=len(pairs), ms=stats["temporal_ms"])

    py_paths = sorted(py_files)
    py_idx = {p: i for i, p in enumerate(py_paths)}
    t0 = time.perf_counter()
    rows_s = chrono.row_normalized(s_edges, py_idx)
    rows_t = chrono.row_normalized({k: v[1] for k, v in pairs.items()}, py_idx)
    stats["rows_ms"] = _ms(t0)
    stats["total_ms"] = _ms(t_all)
    stats["indexed_at"] = time.time()

    idx = RepoIndex(
        repo=repo, rev=sha, repo_dir=repo_dir, base_ts=base_ts, files=files,
        py_files=py_files, py_paths=py_paths, py_idx=py_idx, bm25=bm25,
        blob_cache=bc, s_edges=s_edges, pairs=pairs, rows_s=rows_s,
        rows_t=rows_t, recency=dict(recency), freq=freq, history=history,
        ancestors=ancestors, stats=stats)
    emit("ready", total_ms=stats["total_ms"], rss_mb=rss_mb())
    return idx


def _ms(t0):
    return round((time.perf_counter() - t0) * 1000, 1)


def rss_mb():
    try:
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024)
    except OSError:
        pass
    return None
