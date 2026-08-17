"""In-memory registry of built indexes (LRU) + the acquire/build pipeline."""
import threading
from collections import OrderedDict

import chrono

from .config import settings
from .engine import clone, serving, snapshots


class IndexStore:
    def __init__(self, capacity=None):
        self.capacity = capacity or settings.max_indexes_in_memory
        self._items = OrderedDict()          # id -> RepoIndex
        self._lock = threading.RLock()

    # ---- registry ----------------------------------------------------
    def put(self, index):
        with self._lock:
            self._items[index.id] = index
            self._items.move_to_end(index.id)
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
        return index

    def get(self, index_id):
        with self._lock:
            idx = self._items.get(index_id)
            if idx is not None:
                self._items.move_to_end(index_id)
            return idx

    def loaded(self):
        with self._lock:
            return list(self._items.values())

    # ---- pipeline ----------------------------------------------------
    def ensure(self, repo, rev="HEAD", progress=None):
        """Clone/fetch -> resolve rev -> memory | snapshot | build."""
        def emit(stage, status="done", **info):
            if progress:
                progress(stage, status, **info)

        repo_dir, clone_meta = clone.ensure_repo(repo, progress, rev)
        sha = chrono.git(repo_dir, "rev-parse", rev).strip()
        index_id = f"{repo.replace('/', '__')}@{sha[:12]}"

        hit = self.get(index_id)
        if hit is not None:
            emit("cache", "hit", source="memory", index_id=index_id)
            emit("ready", total_ms=0, index_id=index_id, cached="memory")
            return hit

        snap = snapshots.load(repo, sha)
        if snap is not None:
            emit("cache", "hit", source="snapshot", index_id=index_id)
            self.put(snap)
            emit("ready", total_ms=0, index_id=index_id, cached="snapshot",
                 rss_mb=serving.rss_mb())
            return snap

        index = serving.build_index(repo, repo_dir, sha, progress=progress)
        index.stats["clone"] = clone_meta
        self.put(index)
        try:
            snapshots.save(index)
        except Exception:   # a snapshot is an optimization, never a blocker
            pass
        return index


store = IndexStore()
