"""Persisting a built RepoIndex so a restart (or a booth machine) is instant.

Only the dataclass fields are pickled; everything derived (adjacency,
involvement, raw counts) is rebuilt in __post_init__. `history` is left out
and re-read from chrono.mine_history's own cache, which already exists.
"""
import pickle
import time
from dataclasses import fields
from pathlib import Path

import chrono

from ..config import settings
from .serving import RepoIndex

FORMAT = 3
SKIP = {"history"}


def path_for(repo, rev):
    return settings.snapshots_dir / f"{repo.replace('/', '__')}@{rev[:12]}.pkl"


def save(index):
    payload = {f.name: getattr(index, f.name) for f in fields(index)
               if f.name not in SKIP}
    payload["_format"] = FORMAT
    payload["_saved_at"] = time.time()
    p = path_for(index.repo, index.rev)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(payload, f, protocol=5)
    tmp.replace(p)
    return p


def load(repo, rev):
    p = path_for(repo, rev)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        payload = pickle.load(f)
    if payload.get("_format") != FORMAT:
        return None
    payload.pop("_format", None)
    payload.pop("_saved_at", None)
    repo_dir = Path(payload["repo_dir"])
    cache = settings.cache_dir / f"{repo.replace('/', '__')}_log.pkl"
    payload["history"] = chrono.mine_history(repo_dir, cache)
    return RepoIndex(**payload)


def available():
    """Snapshots on disk: [(repo, rev, mtime, size_mb)]."""
    out = []
    for p in sorted(settings.snapshots_dir.glob("*.pkl")):
        stem = p.stem
        if "@" not in stem:
            continue
        slug, rev = stem.rsplit("@", 1)
        repo = slug.replace("__", "/", 1)
        out.append({"repo": repo, "rev": rev,
                    "saved_at": p.stat().st_mtime,
                    "size_mb": round(p.stat().st_size / 1e6, 1)})
    return out
