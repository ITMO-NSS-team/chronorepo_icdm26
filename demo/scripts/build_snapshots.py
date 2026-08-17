"""Prebuild indexes so a booth machine (or a cold restart) starts instantly.

    python demo/scripts/build_snapshots.py                    # bundled repos
    python demo/scripts/build_snapshots.py --repos psf/requests django/django
    python demo/scripts/build_snapshots.py --instances        # + benchmark revisions

`--instances` additionally builds the index at the base commit of every
featured benchmark issue, which is what makes the recorded gold ranks
reproducible live (the graph must be cut at the pre-fix revision).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.app import bench                                    # noqa: E402
from demo.app.config import settings                          # noqa: E402
from demo.app.engine import clone, serving, snapshots         # noqa: E402


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build(repo, rev="HEAD"):
    t0 = time.time()
    repo_dir, meta = clone.ensure_repo(repo, rev=rev)
    log(f"{repo}: {meta['action']} {meta.get('mb', '?')} MB "
        f"in {meta['ms'] / 1000:.1f}s")
    index = serving.build_index(repo, repo_dir, rev)
    path = snapshots.save(index)
    log(f"{repo}@{index.rev[:12]}: {len(index.py_files)} py files, "
        f"{len(index.s_edges)} import edges, {len(index.pairs)} co-change "
        f"pairs, index {index.stats['total_ms'] / 1000:.1f}s, "
        f"RSS {serving.rss_mb()} MB -> {path.name} "
        f"({path.stat().st_size / 1e6:.1f} MB, {time.time() - t0:.0f}s total)")
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*", default=list(settings.bundled_repos))
    ap.add_argument("--instances", action="store_true",
                    help="also build the base commit of every featured issue")
    args = ap.parse_args()

    for repo in args.repos:
        try:
            build(repo)
        except Exception as e:
            log(f"{repo}: FAILED {type(e).__name__}: {e}")

    if args.instances:
        for inst in bench.instances():
            if not inst["featured"] or inst["repo"] not in args.repos:
                continue
            try:
                build(inst["repo"], inst["base_commit"])
            except Exception as e:
                log(f"{inst['id']}: FAILED {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
