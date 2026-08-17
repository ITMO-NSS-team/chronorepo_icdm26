"""Background indexing jobs with an SSE-friendly event log."""
import threading
import time
import traceback
import uuid
from collections import deque

from .config import settings
from .store import store


class Job:
    def __init__(self, repo, rev):
        self.id = uuid.uuid4().hex[:12]
        self.repo, self.rev = repo, rev
        self.events = []
        self.state = "queued"          # queued|running|done|error
        self.index_id = None
        self.error = None
        self.started = time.time()
        self._cv = threading.Condition()

    def emit(self, stage, status="done", **info):
        ev = {"stage": stage, "status": status, "t": round(
            time.time() - self.started, 3), **info}
        with self._cv:
            self.events.append(ev)
            self._cv.notify_all()

    def finish(self, state, index_id=None, error=None):
        self.state, self.index_id, self.error = state, index_id, error
        self.emit("finished", state, index_id=index_id, error=error)

    def wait_for(self, cursor, timeout=15.0):
        """Block until there is an event after `cursor` (or timeout)."""
        with self._cv:
            if cursor < len(self.events):
                return self.events[cursor:]
            self._cv.wait(timeout)
            return self.events[cursor:]


class JobManager:
    def __init__(self):
        self.jobs = {}
        self.order = deque(maxlen=200)
        self._sem = threading.BoundedSemaphore(
            settings.max_concurrent_index_jobs)
        self._lock = threading.Lock()

    def submit(self, repo, rev="HEAD"):
        job = Job(repo, rev)
        with self._lock:
            self.jobs[job.id] = job
            self.order.append(job.id)
            for old in list(self.jobs):
                if old not in self.order:
                    self.jobs.pop(old, None)
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def _run(self, job):
        if not self._sem.acquire(timeout=0.1):
            job.emit("queue", "waiting",
                     message="another repository is indexing")
            self._sem.acquire()
        job.state = "running"
        try:
            index = store.ensure(job.repo, job.rev, progress=job.emit)
            job.finish("done", index_id=index.id)
        except Exception as e:                       # surfaced to the UI
            job.finish("error", error=f"{type(e).__name__}: {e}")
            job.events.append({"stage": "traceback", "status": "debug",
                               "text": traceback.format_exc()[-1500:]})
        finally:
            self._sem.release()

    def get(self, job_id):
        return self.jobs.get(job_id)


manager = JobManager()
