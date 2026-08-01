"""ChronoRepo experiment library — E1/E2 pilot for the ICDM'26 demo.

Pure stdlib. All repo access goes through git plumbing on a bare clone
(ls-tree / cat-file / log / rev-list), so nothing is ever checked out and
the history cutoff at each instance's base commit is exact (rev-list
ancestor set — no time-based approximation, no future leakage).
"""
import ast
import math
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)  # old blobs' docstrings
import pickle
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- git helpers

def git(repo_dir, *args, check=True):
    """Run git in repo_dir, return stdout as str (utf-8, errors replaced)."""
    p = subprocess.run(["git", "-C", str(repo_dir), *args],
                       capture_output=True, check=False)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: "
                           f"{p.stderr.decode('utf-8', 'replace')[:300]}")
    return p.stdout.decode("utf-8", "replace")


def git_bytes(repo_dir, *args):
    p = subprocess.run(["git", "-C", str(repo_dir), *args],
                       capture_output=True, check=True)
    return p.stdout


# ---------------------------------------------------------------- tokenization

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_STOP = frozenset("""the a an and or not is are was were be been being have has
had do does did will would can could should this that these those with from
for into onto out in on at by of to as if then else when while return def
class import self none true false pass raise try except finally lambda yield
assert global del print""".split())


def subtokens(tok):
    """foo_barBaz -> [foo, bar, baz] (plus the original, lowered)."""
    out = []
    for part in tok.split("_"):
        for sub in _CAMEL.split(part):
            s = sub.lower()
            if len(s) > 1 and s not in _STOP:
                out.append(s)
    low = tok.lower()
    if len(low) > 1 and low not in _STOP and low not in out:
        out.append(low)
    return out


def tokenize(text, cap=60000):
    """BM25 tokens: identifiers + their subtokens, lowercased."""
    toks = []
    for m in _IDENT.finditer(text[:cap * 8]):
        toks.extend(subtokens(m.group()))
        if len(toks) >= cap:
            break
    return toks


def issue_identifiers(text):
    """Code-looking identifiers in an issue: for the grep-style seed."""
    idents = set()
    for m in _IDENT.finditer(text):
        t = m.group()
        if len(t) < 3 or t.lower() in _STOP:
            continue
        if "_" in t or (not t.isupper() and not t.islower()):  # snake or Camel
            idents.add(t)
    for m in re.finditer(r"[`'\"]([A-Za-z_][A-Za-z0-9_./]{2,})[`'\"]", text):
        idents.add(m.group(1).split("/")[-1].removesuffix(".py"))
    return idents


# ---------------------------------------------------------------- blob parsing

_PY2_FALLBACK = re.compile(
    r"^\s*(?:from\s+([.\w]+)\s+import|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))",
    re.M)


def parse_imports(src, pkg_parts):
    """Return set of absolute dotted module strings imported by a python blob.
    pkg_parts: dotted package path of the *containing package* of this file,
    used to resolve relative imports."""
    mods = set()
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    mods.add(a.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    if node.module:
                        mods.add(node.module)
                else:  # relative
                    base = pkg_parts[:len(pkg_parts) - (node.level - 1)]
                    if node.module:
                        mods.add(".".join([*base, node.module]))
                    else:
                        for a in node.names:
                            mods.add(".".join([*base, a.name]))
    except SyntaxError:  # py2-era blob etc.
        for m in _PY2_FALLBACK.finditer(src):
            frm, imp = m.groups()
            if frm:
                mods.add(frm.lstrip("."))
            elif imp:
                for part in imp.split(","):
                    mods.add(part.strip())
    return mods


TEXT_EXT = {".py", ".rst", ".md", ".txt", ".cfg", ".ini", ".toml", ".yml",
            ".yaml"}
MAX_BLOB = 300_000  # bytes


class BlobCache:
    """Per-repo cache keyed by blob sha: token counter, ident set, imports."""

    def __init__(self, repo_dir):
        self.repo_dir = repo_dir
        self.tokens = {}    # sha -> Counter (capped)
        self.idents = {}    # sha -> frozenset of raw identifiers
        self.imports = {}   # (sha, pkg) -> set of dotted modules

    def load_missing(self, wanted):
        """Fetch blob contents for shas not yet cached. wanted: {sha: path}."""
        missing = [s for s in set(wanted.values()) if s not in self.tokens]
        for i in range(0, len(missing), 400):
            chunk = missing[i:i + 400]
            inp = ("\n".join(chunk) + "\n").encode()
            p = subprocess.run(["git", "-C", str(self.repo_dir), "cat-file",
                                "--batch"], input=inp, capture_output=True,
                               check=True)
            buf, pos = p.stdout, 0
            for sha in chunk:
                nl = buf.index(b"\n", pos)
                header = buf[pos:nl].decode("ascii", "replace").split()
                size = int(header[2]) if len(header) == 3 else 0
                body = buf[nl + 1:nl + 1 + size]
                pos = nl + 1 + size + 1  # trailing newline
                if size > MAX_BLOB:
                    body = body[:MAX_BLOB]
                src = body.decode("utf-8", "replace")
                self.tokens[sha] = Counter(
                    dict(Counter(tokenize(src)).most_common(2000)))
                self.idents[sha] = frozenset(
                    m.group() for m in _IDENT.finditer(src[:400_000]))

    def imports_of(self, sha, path, src_getter):
        pkg = pkg_of(path)
        key = (sha, pkg)
        if key not in self.imports:
            self.imports[key] = parse_imports(src_getter(), pkg.split(".")
                                              if pkg else [])
        return self.imports[key]

    def maybe_trim(self, cap=40000):
        if len(self.tokens) > cap:
            self.tokens.clear()
            self.idents.clear()
            self.imports.clear()


def pkg_of(path):
    """Containing package of a .py file as dotted string ('' at repo root)."""
    parts = path.split("/")[:-1]
    return ".".join(parts)


# ---------------------------------------------------------------- history mining

_RENAME_BRACE = re.compile(r"\{[^{}]* => ([^{}]*)\}")


def _clean_path(p):
    p = _RENAME_BRACE.sub(lambda m: m.group(1), p)
    if " => " in p:
        p = p.split(" => ")[-1]
    return p.replace("//", "/").lstrip("/")


def mine_history(repo_dir, cache_file, max_files_per_commit=30):
    """One pass over the full history: [(sha, unix_ts, [py paths])].
    Cached to disk; the per-instance ancestor filter happens later."""
    cache_file = Path(cache_file)
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    out = []
    raw = git_bytes(repo_dir, "log", "--all", "--numstat",
                    "--format=%x01%H%x09%ct")
    sha = ts = None
    files = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.startswith("\x01"):
            if sha and files:
                out.append((sha, ts, files))
            sha, ts_s = line[1:].split("\t")
            ts = int(ts_s)
            files = []
        elif line and "\t" in line:
            parts = line.split("\t")
            if len(parts) == 3:
                p = _clean_path(parts[2])
                if p.endswith(".py"):
                    files.append(p)
    if sha and files:
        out.append((sha, ts, files))
    out = [(s, t, f) for (s, t, f) in out if len(f) <= max_files_per_commit]
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(out, f, protocol=4)
    return out


def ancestor_set(repo_dir, base_commit):
    try:
        return set(git(repo_dir, "rev-list", base_commit).split())
    except RuntimeError:
        # PR-branch commits are not reachable from cloned refs;
        # GitHub serves arbitrary SHAs on direct fetch.
        git(repo_dir, "fetch", "origin", base_commit, check=False)
        return set(git(repo_dir, "rev-list", base_commit).split())


def tree_at(repo_dir, base_commit):
    """{path: blob_sha} for text-ish files at base_commit."""
    files = {}
    for line in git(repo_dir, "ls-tree", "-r", base_commit).splitlines():
        try:
            meta, path = line.split("\t", 1)
            mode, typ, sha = meta.split()
        except ValueError:
            continue
        if typ != "blob":
            continue
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        if ext in TEXT_EXT:
            files[path] = sha
    return files


# ---------------------------------------------------------------- graphs

def temporal_edges(history, ancestors, base_ts, lam_per_day, file_set):
    """{(a,b): weight} over unordered pairs of files alive at base."""
    edges = defaultdict(float)
    for sha, ts, files in history:
        if sha not in ancestors:
            continue
        alive = [f for f in files if f in file_set]
        if len(alive) < 2:
            continue
        if lam_per_day > 0:
            age_days = max(0.0, (base_ts - ts) / 86400.0)
            w = math.exp(-lam_per_day * age_days)
        else:
            w = 1.0
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                a, b = sorted((alive[i], alive[j]))
                edges[(a, b)] += w
    return edges


def static_edges(files, blob_cache, repo_dir):
    """{(a,b): 1.0} from import resolution among .py files at base."""
    py_files = [p for p in files if p.endswith(".py")]
    module_map = {}
    for p in py_files:
        dotted = p[:-3].replace("/", ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        aliases = {dotted}
        parts = dotted.split(".")
        for strip in ("src", "lib"):
            if parts and parts[0] == strip:
                aliases.add(".".join(parts[1:]))
        for a in aliases:
            if a:
                module_map.setdefault(a, p)

    def resolve(mod):
        parts = mod.split(".")
        for i in range(len(parts), 0, -1):
            hit = module_map.get(".".join(parts[:i]))
            if hit:
                return hit
        return None

    edges = {}
    for p in py_files:
        sha = files[p]
        def getter(sha=sha):
            raw = git_bytes(repo_dir, "cat-file", "blob", sha)[:MAX_BLOB]
            return raw.decode("utf-8", "replace")
        for mod in blob_cache.imports_of(sha, p, getter):
            q = resolve(mod)
            if q and q != p:
                edges[tuple(sorted((p, q)))] = 1.0
    return edges


def row_normalized(edges, nodes_idx):
    """Undirected weighted edge dict -> row-normalized sparse rows
    {i: [(j, w), ...]}."""
    adj = defaultdict(list)
    for (a, b), w in edges.items():
        ia, ib = nodes_idx.get(a), nodes_idx.get(b)
        if ia is None or ib is None or w <= 0:
            continue
        adj[ia].append((ib, w))
        adj[ib].append((ia, w))
    rows = {}
    for i, nbrs in adj.items():
        s = sum(w for _, w in nbrs)
        rows[i] = [(j, w / s) for j, w in nbrs]
    return rows


def mix_rows(rows_s, rows_t, alpha, n):
    if alpha >= 1.0:
        return rows_s
    if alpha <= 0.0:
        return rows_t
    mixed = {}
    for i in range(n):
        acc = defaultdict(float)
        for j, w in rows_s.get(i, ()):
            acc[j] += alpha * w
        for j, w in rows_t.get(i, ()):
            acc[j] += (1 - alpha) * w
        if acc:
            mixed[i] = list(acc.items())
    return mixed


def ppr(rows, seed_vec, n, damping=0.5, iters=10):
    p = list(seed_vec)
    for _ in range(iters):
        nxt = [0.0] * n
        for i, pi in enumerate(p):
            if pi <= 0:
                continue
            nbrs = rows.get(i)
            if not nbrs:
                nxt[i] += damping * pi  # dangling: stay put
                continue
            for j, w in nbrs:
                nxt[j] += damping * pi * w
        for i in range(n):
            nxt[i] += (1 - damping) * seed_vec[i]
        p = nxt
    return p


# ---------------------------------------------------------------- retrieval

class BM25:
    K1, B = 1.2, 0.75

    def __init__(self, docs):
        """docs: {path: Counter}"""
        self.paths = list(docs)
        self.tf = [docs[p] for p in self.paths]
        self.dl = [max(1, sum(c.values())) for c in self.tf]
        self.avgdl = sum(self.dl) / max(1, len(self.dl))
        self.N = len(self.paths)
        df = Counter()
        self.post = defaultdict(list)  # token -> [doc ids]
        for i, c in enumerate(self.tf):
            for t in c:
                df[t] += 1
                self.post[t].append(i)
        self.idf = {t: math.log((self.N - d + 0.5) / (d + 0.5) + 1)
                    for t, d in df.items()}

    def query(self, tokens, top=50):
        q = Counter(tokens)
        scores = defaultdict(float)
        for t in q:
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i in self.post[t]:
                f = self.tf[i][t]
                dl = self.dl[i]
                scores[i] += idf * f * (self.K1 + 1) / (
                    f + self.K1 * (1 - self.B + self.B * dl / self.avgdl))
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:top]
        return [(self.paths[i], s) for i, s in ranked]


def grep_scores(idents, files, blob_cache, top=50):
    """Cheap grep-style seed: idf-weighted identifier membership + path hits."""
    df = Counter()
    hits = {}
    for p, sha in files.items():
        blob_idents = blob_cache.idents.get(sha, frozenset())
        h = [t for t in idents if t in blob_idents]
        if h:
            hits[p] = h
            for t in h:
                df[t] += 1
    n = max(1, len(files))
    scores = {}
    for p, h in hits.items():
        s = sum(math.log(n / (1 + df[t])) for t in h)
        base = p.rsplit("/", 1)[-1].removesuffix(".py").lower()
        s += sum(2.0 for t in idents if t.lower() in base or base in t.lower())
        scores[p] = s
    return sorted(scores.items(), key=lambda kv: -kv[1])[:top]


def hybrid_rank(seed_list, rows, py_idx, n_py, all_paths, beta=0.5, top=50,
                return_scores=False):
    """seed_list: [(path, score)] over all files. PPR runs on .py nodes;
    final = beta * seed + (1-beta) * ppr, both max-normalized."""
    seed_vec = [0.0] * n_py
    tot = sum(s for _, s in seed_list[:20]) or 1.0
    for p, s in seed_list[:20]:
        i = py_idx.get(p)
        if i is not None:
            seed_vec[i] += s / tot
    pv = ppr(rows, seed_vec, n_py)
    pmax = max(pv) or 1.0
    smax = (seed_list[0][1] if seed_list else 1.0) or 1.0
    seed_d = dict(seed_list)
    final = {}
    for p in all_paths:
        s = beta * seed_d.get(p, 0.0) / smax
        i = py_idx.get(p)
        if i is not None:
            s += (1 - beta) * pv[i] / pmax
        if s > 0:
            final[p] = s
    ranked = sorted(final.items(), key=lambda kv: -kv[1])[:top]
    return ranked if return_scores else [p for p, _ in ranked]


# ---------------------------------------------------------------- metrics / E1

def eval_ranking(ranked, gold):
    gold = set(gold)
    if not gold:
        return {}
    res = {}
    for k in (1, 5, 10):
        topk = ranked[:k]
        res[f"r{k}"] = len(gold & set(topk)) / len(gold)
        res[f"hit{k}"] = 1.0 if gold & set(topk) else 0.0
    ap, found = 0.0, 0
    for rank, p in enumerate(ranked[:50], 1):
        if p in gold:
            found += 1
            ap += found / rank
    res["ap"] = ap / len(gold)
    return res


def e1_orthogonality(s_edges, t_edges, k=10, min_deg=3):
    """Median Jaccard of top-k neighbor sets, files with >=min_deg in both."""
    def nbrs(edges):
        d = defaultdict(dict)
        for (a, b), w in edges.items():
            d[a][b] = w
            d[b][a] = w
        return d
    ns, nt = nbrs(s_edges), nbrs(t_edges)
    js = []
    for f in set(ns) & set(nt):
        if len(ns[f]) < min_deg or len(nt[f]) < min_deg:
            continue
        top_s = set(sorted(ns[f], key=ns[f].get, reverse=True)[:k])
        top_t = set(sorted(nt[f], key=nt[f].get, reverse=True)[:k])
        js.append(len(top_s & top_t) / len(top_s | top_t))
    if not js:
        return None
    js.sort()
    return {"n_files": len(js), "median": js[len(js) // 2],
            "mean": sum(js) / len(js)}


def gold_files_from_patch(patch):
    gold = set()
    for m in re.finditer(r"^diff --git a/(.+?) b/(.+)$", patch, re.M):
        p = m.group(2).strip()
        if p != "/dev/null":
            gold.add(p)
    return sorted(gold)
