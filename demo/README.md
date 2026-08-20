# ChronoRepo demo application

A web app around the engine in `experiments/chrono.py`: index any GitHub
repository live, watch its temporal graph, ask for the impact set of a file,
and localize a real issue with BM25 / candidates / one small-model call side
by side, with real latency and cost meters.

Nothing on the screen is precomputed for show. Indexing progress is the
pipeline reporting its own stages, rankings come from
`night_lab.rrf_final`'s recipe, the cost meter is OpenRouter's token
accounting. `tests/test_parity.py` asserts that the baskets this app produces
are byte-identical to the ones the reported runs consumed.

## Run

```bash
python -m venv demo/.venv && demo/.venv/bin/pip install -e demo[test]
cd demo/web && npm install && npm run build && cd ../..     # once
demo/.venv/bin/python -m uvicorn app.main:app --app-dir demo --port 8000
# http://localhost:8000
```

Frontend development (hot reload, API proxied to :8000):

```bash
cd demo/web && npm run dev        # http://localhost:5173
```

The LLM rerank needs an OpenRouter key: `OPENROUTER_API_KEY` in the repo-root
`.env` (or `experiments/.openrouter_key`). Without it the app runs fine and
the third column simply stays empty.

## The demo path

The app is one scenario read top to bottom; every step carries a brief and a
`Next` button, so it can be handed to a visitor without narration.

| step | what happens |
|---|---|
| 01 Index | paste a GitHub URL (or click a bundled repo); the log is the pipeline's own stages |
| 02 Graph | both layers over the same files; the slider ages the co-change weights |
| 03 Impact set | pick a file, get what changes with it, with the evidence per row |
| 04 Localize an issue | the main event: BM25 vs candidates vs one small-model call |
| 05 Results | the paper's tables and the cost/accuracy frontier |

Step 04 preloads a featured benchmark issue for the indexed repository, so a
cold visitor is one click from an answer.

## Modes

`CHRONO_MODE` selects what the app is allowed to do:

| mode | behaviour |
|---|---|
| `live` (default) | clones any GitHub repository on demand |
| `snapshot` | only repositories already in `demo/var/repos` / `demo/snapshots` |
| `booth` | same as snapshot; use with `CHRONO_ALLOW_LLM=0` for a network-free session |

Prebuild what the booth machine will need:

```bash
demo/.venv/bin/python demo/scripts/build_snapshots.py --instances
```

Other knobs: `CHRONO_MODEL`, `CHRONO_MAX_INDEXES`, `CHRONO_INDEX_RATE`,
`CHRONO_LLM_RATE`, `CHRONO_MAX_REPO_MB`, `CHRONO_CORS`.

## Layout

```
app/
  main.py            FastAPI routes + SSE indexing stream + SPA hosting
  config.py          settings, .env, sys.path bootstrap for experiments/
  store.py           LRU of built indexes; clone -> snapshot -> build pipeline
  jobs.py            background indexing jobs with an event log
  bench.py           benchmark issues, recorded runs, the paper's tables
  engine/
    serving.py       RepoIndex + localize/impact/subgraph  (the core)
    evidence.py      evidence chips; render() == prepare_rerank50.evidence_str
    clone.py         GitHub URL validation, bare clone/fetch with progress
    snapshots.py     pickled indexes for instant restarts
    rerank.py        the one LLM call: run_rerank's prompt, real token cost
data/leaderboard.json   the paper's tables (Tables I-V of main.tex)
web/                 Vite + React + TypeScript + sigma.js frontend
                     (Newsreader + IBM Plex Mono, bundled via @fontsource:
                      `npm run build` needs no network at demo time)
scripts/             snapshot prebuilder
tests/               parity with the reported runs, API smoke tests
legacy/              the original single-file prototype, kept for reference
var/                 clones and history caches (gitignored)
```

## The engine split

`night_lab.build_context()` is written for one benchmark instance: it
rebuilds tree, blobs, BM25 and both graph layers on every call. Serving needs
the same computation split in two — `serving.RepoIndex` holds everything that
depends only on the revision, and `localize()` computes only the
issue-dependent seeds per query:

| operation | measured (this machine) |
|---|---|
| index pallets/flask at HEAD (clone cached) | 0.6 s |
| index django at a benchmark base commit | see `stats` in `/api/repos/{id}` |
| `localize` without the LLM call | ~5-11 ms |
| `impact` (five methods) | ~4 ms |
| subgraph for the graph view | ~2.5 ms |
| one `qwen-2.5-7b-instruct` call over 50 candidates | 1.1 s, $0.00006 |

The candidate recipe is not reimplemented: `serving._fuse` reproduces
`night_lab.rrf_final(k=40, exclude=("gr",))` list for list, and the tests
fail if it ever drifts.

## Tests

```bash
demo/.venv/bin/python -m pytest demo/tests -q
```

`test_parity.py` clones a few small repositories on first run and checks:

* `_fuse` == `night_lab.rrf_final` (with provenance that sums to the score);
* the live basket == `data/rerank_final_lite.jsonl` for four real instances;
* the single-pass pair miner == `chrono.temporal_edges` (decayed and raw);
* evidence chips render to `prepare_rerank50.evidence_str`'s exact strings;
* no commit outside the base commit's ancestry enters the graph;
* the timeline slider's client-side decay formula reproduces the server's
  weights from the per-edge commit stamps.

## API

| method | path | notes |
|---|---|---|
| `GET` | `/api/config` | modes, models, λ, α, RRF k |
| `POST` | `/api/index` | `{repo, rev?}` → `job_id` (GitHub URLs only) |
| `GET` | `/api/index/{job}/events` | SSE: clone → history → tree → blobs → imports → temporal → ready |
| `GET` | `/api/repos/{id}` | stats, stage timings, most co-changed files |
| `GET` | `/api/repos/{id}/graph` | subgraph + per-edge commit stamps for the slider |
| `GET` | `/api/repos/{id}/impact` | ROSE / freq / static / temporal / hybrid, with evidence |
| `POST` | `/api/repos/{id}/localize` | BM25, candidates with RRF provenance, optional LLM call |
| `GET` | `/api/instances` | SWE-bench Lite issues with gold files and recorded runs |
| `GET` | `/api/benchmarks` | the paper's tables and the cost/accuracy Pareto |

## Security notes

`/api/index` runs `git` against user input, so only
`https://github.com/<owner>/<repo>` is accepted (no ssh, no `file://`, no
other hosts), repository size is checked against the GitHub API before
cloning, git runs without a shell and with a timeout, concurrent index jobs
are capped, and both `/api/index` and the LLM path are rate-limited per IP.
The OpenRouter key never leaves the server.
