"""Top-100 union baskets for LocBench + code skeletons for the top-20.

Skeleton = first docstring line + up to 12 class/def signature lines,
extracted from the blob at the instance's base commit (~500 chars).
Output: data/rerank_input100.jsonl. Resumable."""
import json
import re
import subprocess
import time
import traceback
from pathlib import Path

import chrono

HERE = Path(__file__).parent
OUT = HERE / "data" / "rerank_input100.jsonl"
TOP = 100
SNIPPET_TOP = 20

_SIG = re.compile(r"^(?:class |def |    def )[^\n]*", re.M)
_DOC = re.compile(r'^\s*(?:"""|\'\'\')(.{0,120})', re.M)


def skeleton(src):
    parts = []
    m = _DOC.search(src[:2000])
    if m and m.group(1).strip():
        parts.append('"""' + m.group(1).strip())
    parts.extend(s.strip() for s in _SIG.findall(src)[:12])
    return " | ".join(parts)[:500]


def blob_texts(repo_dir, shas):
    if not shas:
        return {}
    inp = ("\n".join(shas) + "\n").encode()
    p = subprocess.run(["git", "-C", str(repo_dir), "cat-file", "--batch"],
                       input=inp, capture_output=True, check=True)
    out, buf, pos = {}, p.stdout, 0
    for sha in shas:
        nl = buf.index(b"\n", pos)
        header = buf[pos:nl].decode("ascii", "replace").split()
        size = int(header[2]) if len(header) == 3 else 0
        out[sha] = buf[nl + 1:nl + 1 + min(size, 60000)].decode(
            "utf-8", "replace")
        pos = nl + 1 + size + 1
    return out


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    done = set()
    if OUT.exists():
        for line in open(OUT, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    insts = [json.loads(l) for l in open(HERE / "data" / "locbench.jsonl",
                                         encoding="utf-8")]
    valid = set()
    for line in open(HERE / "results" / "results_locbench.jsonl",
                     encoding="utf-8"):
        r = json.loads(line)
        if "configs" in r:
            valid.add(r["instance_id"])
    todo = [i for i in insts if i["instance_id"] in valid
            and i["instance_id"] not in done]
    log(f"{len(todo)} instances to prepare")

    out = open(OUT, "a", encoding="utf-8")
    cur_repo, bc = None, None
    for k, inst in enumerate(sorted(todo, key=lambda x: x["repo"])):
        try:
            repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__")
                                         + ".git")
            if inst["repo"] != cur_repo:
                cur_repo = inst["repo"]
                bc = chrono.BlobCache(repo_dir)
            history = chrono.mine_history(
                repo_dir, HERE / "cache" / (inst["repo"].replace("/", "__")
                                            + "_log.pkl"))
            base = inst["base_commit"]
            gold = chrono.gold_files_from_patch(inst["patch"])
            ancestors = chrono.ancestor_set(repo_dir, base)
            files = chrono.tree_at(repo_dir, base)
            py_files = {p: s for p, s in files.items() if p.endswith(".py")}
            base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                                     base).strip())
            bc.load_missing(files)
            docs = {p: bc.tokens[s] for p, s in files.items()
                    if s in bc.tokens}
            bm25 = chrono.BM25(docs)
            seed_list = bm25.query(
                chrono.tokenize(inst["problem_statement"], cap=3000))
            grep_list = chrono.grep_scores(
                chrono.issue_identifiers(inst["problem_statement"]),
                files, bc)
            s_edges = chrono.static_edges(files, bc, repo_dir)
            t_dec = chrono.temporal_edges(history, ancestors, base_ts,
                                          1 / 90, set(py_files))
            py_paths = sorted(py_files)
            py_idx = {p: i for i, p in enumerate(py_paths)}
            n_py = len(py_paths)
            rows = chrono.mix_rows(chrono.row_normalized(s_edges, py_idx),
                                   chrono.row_normalized(t_dec, py_idx),
                                   0.25, n_py)
            hyb_bm = chrono.hybrid_rank(seed_list, rows, py_idx, n_py,
                                        list(files), top=80)
            hyb_gr = chrono.hybrid_rank(grep_list, rows, py_idx, n_py,
                                        list(files), top=30)
            hybrid = list(dict.fromkeys(
                hyb_bm + hyb_gr + [p for p, _ in seed_list[:15]]))[:TOP]
            snip_paths = hybrid[:SNIPPET_TOP]
            texts = blob_texts(repo_dir,
                               [files[p] for p in snip_paths if p in files])
            cands = []
            for j, p in enumerate(hybrid):
                c = {"file": p}
                if j < SNIPPET_TOP and p in files:
                    c["snippet"] = skeleton(texts.get(files[p], ""))
                cands.append(c)
            out.write(json.dumps({
                "instance_id": inst["instance_id"],
                "repo": inst["repo"],
                "category": inst.get("category"),
                "issue": inst["problem_statement"][:1500],
                "gold": gold,
                "hybrid_top": cands,
            }) + "\n")
            out.flush()
            if (k + 1) % 50 == 0:
                log(f"{k + 1}/{len(todo)}")
            bc.maybe_trim()
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    out.close()
    log("PREP100 DONE")


if __name__ == "__main__":
    main()
