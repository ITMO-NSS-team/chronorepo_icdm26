"""ChronoRepo demo API.

Everything the UI shows is computed by experiments/chrono.py through
app/engine/serving.py: indexing progress is the real pipeline reporting its
own stages, rankings are the paper's recipe, the cost meter is OpenRouter's
own token accounting.
"""
import asyncio
import json
import time
from collections import defaultdict, deque

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import bench
from .config import settings
from .engine import clone, rerank, serving, snapshots
from .jobs import manager
from .store import store

app = FastAPI(title="ChronoRepo demo", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"], allow_headers=["*"])

_hits = defaultdict(lambda: deque(maxlen=120))


def rate_limit(request: Request, bucket: str, per_min: int):
    key = (bucket, request.client.host if request.client else "?")
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= per_min:
        raise HTTPException(429, f"Rate limit: {per_min} {bucket}/min")
    q.append(now)


def get_index(index_id):
    idx = store.get(index_id)
    if idx is None:
        raise HTTPException(404, f"Index {index_id} is not loaded; "
                                 f"index the repository first")
    return idx


# ------------------------------------------------------------------ meta

@app.get("/api/config")
def api_config():
    return {
        "mode": settings.mode,
        "llm": {
            "enabled": settings.allow_llm and bool(settings.openrouter_key()),
            "models": [{"id": m, "label": lbl, "note": note}
                       for m, lbl, note in settings.models],
            "default": settings.default_model,
        },
        "bundled_repos": list(settings.bundled_repos),
        "lambda_per_day": serving.LAM,
        "alpha": serving.ALPHA,
        "rrf_k": serving.RRF_K,
        "candidate_depth": serving.TOP,
    }


@app.get("/api/repos")
def api_repos():
    loaded = [{"index_id": i.id, "repo": i.repo, "rev": i.rev,
               "stats": i.stats, "state": "loaded"} for i in store.loaded()]
    have = {(s["repo"], s["rev"]) for s in snapshots.available()}
    snaps = [{"repo": r, "rev": v, "state": "snapshot"} for r, v in have]
    return {"loaded": loaded, "snapshots": snaps,
            "suggested": list(settings.bundled_repos)}


# ------------------------------------------------------------------ indexing

@app.post("/api/index")
def api_index(request: Request, payload: dict = Body(...)):
    rate_limit(request, "index", settings.index_rate_per_min)
    try:
        repo = clone.parse_repo(payload.get("repo") or payload.get("url"))
    except clone.RepoError as e:
        raise HTTPException(400, str(e)) from None
    rev = (payload.get("rev") or "HEAD").strip()
    if not rev.replace("^", "").replace("~", "").replace("-", "") \
            .replace("_", "").replace("/", "").replace(".", "").isalnum():
        raise HTTPException(400, "Invalid revision")
    job = manager.submit(repo, rev)
    return {"job_id": job.id, "repo": repo, "rev": rev}


@app.get("/api/index/{job_id}/events")
async def api_index_events(job_id: str):
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job")

    async def stream():
        cursor = 0
        while True:
            events = await asyncio.to_thread(job.wait_for, cursor, 10.0)
            for ev in events:
                cursor += 1
                yield f"event: {ev['stage']}\ndata: {json.dumps(ev)}\n\n"
            if job.state in ("done", "error") and cursor >= len(job.events):
                yield ("event: end\ndata: "
                       + json.dumps({"state": job.state,
                                     "index_id": job.index_id,
                                     "error": job.error}) + "\n\n")
                return
            if not events:
                yield ": keepalive\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/api/index/{job_id}")
def api_job(job_id: str):
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job")
    return {"job_id": job.id, "repo": job.repo, "state": job.state,
            "index_id": job.index_id, "error": job.error,
            "events": job.events}


# ------------------------------------------------------------------ repo views

@app.get("/api/repos/{index_id}")
def api_repo(index_id: str):
    idx = get_index(index_id)
    span = [min((v[2] for v in idx.pairs.values()), default=idx.base_ts),
            idx.base_ts]
    return {
        "index_id": idx.id, "repo": idx.repo, "rev": idx.rev,
        "base_ts": idx.base_ts, "span": span,
        "stats": {**idx.stats,
                  "py_files": len(idx.py_files),
                  "files": len(idx.files),
                  "import_edges": len(idx.s_edges),
                  "cochange_pairs": len(idx.pairs),
                  "commits_in_ancestry": len(idx.ancestors),
                  "rss_mb": serving.rss_mb()},
        "top_files": [{"file": p, "involvement": int(c),
                       "changes": int(idx.freq.get(p, 0))}
                      for p, c in idx.involvement.most_common(40)],
    }


@app.get("/api/repos/{index_id}/graph")
def api_graph(index_id: str, focus: str | None = None,
              limit: int = Query(140, ge=10, le=1200),
              min_count: int = Query(2, ge=1, le=50)):
    idx = get_index(index_id)
    t0 = time.perf_counter()
    data = idx.subgraph(focus=focus, limit=limit, min_count=min_count)
    data["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return data


@app.get("/api/repos/{index_id}/search")
def api_search(index_id: str, q: str, limit: int = 30):
    return {"files": get_index(index_id).search(q, limit)}


@app.get("/api/repos/{index_id}/impact")
def api_impact(index_id: str, file: str, k: int = Query(15, ge=1, le=50)):
    idx = get_index(index_id)
    try:
        return idx.impact(file, k=k)
    except KeyError:
        raise HTTPException(404, f"{file} is not a .py file at this "
                                 f"revision") from None


@app.post("/api/repos/{index_id}/localize")
def api_localize(index_id: str, request: Request, payload: dict = Body(...)):
    idx = get_index(index_id)
    issue = (payload.get("issue") or "").strip()
    instance_id = payload.get("instance_id")
    gold = payload.get("gold") or []
    if instance_id and not issue:
        inst = bench.instance(instance_id)
        if not inst:
            raise HTTPException(404, "Unknown instance")
        issue, gold = inst["issue"], inst["gold"]
    if len(issue) < 12:
        raise HTTPException(400, "Issue text is too short")

    depth = int(payload.get("depth") or 50)
    depth = max(10, min(100, depth))
    result = idx.localize(issue, depth=depth)
    result["gold"] = gold
    result["depth"] = depth
    result["instance_id"] = instance_id

    llm = payload.get("llm") or {}
    if llm.get("enabled"):
        rate_limit(request, "llm", settings.llm_rate_per_min)
        if not settings.allow_llm:
            raise HTTPException(403, "LLM calls are disabled in this mode")
        paths = result["candidate_paths"][:depth]
        try:
            call = rerank.call(issue, paths, model=llm.get("model"))
        except rerank.LLMError as e:
            result["llm_error"] = str(e)
        else:
            ranked = call.pop("ranked")
            result["final"] = ranked + [p for p in paths if p not in ranked]
            result["llm"] = call
            result["timings_ms"]["llm"] = call["ms"]
    return result


# ------------------------------------------------------------------ bench

@app.get("/api/instances")
def api_instances(repo: str | None = None, limit: int = 200):
    return {"instances": bench.instances(repo=repo, limit=limit)}


@app.get("/api/instances/{instance_id}")
def api_instance(instance_id: str):
    inst = bench.instance(instance_id)
    if not inst:
        raise HTTPException(404, "Unknown instance")
    return inst


@app.get("/api/benchmarks")
def api_benchmarks():
    return bench.leaderboard()


# ------------------------------------------------------------------ static

if settings.web_dist.exists():
    app.mount("/assets", StaticFiles(directory=settings.web_dist / "assets"),
              name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Unknown endpoint")
        root = settings.web_dist.resolve()
        candidate = (root / full_path).resolve()
        # the path converter accepts "..": never serve outside the bundle
        if full_path and candidate.is_file() \
                and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(root / "index.html")
else:
    @app.get("/")
    def no_ui():
        return JSONResponse({
            "error": "UI is not built",
            "hint": "cd demo/web && npm install && npm run build",
        }, status_code=503)
