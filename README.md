# ChronoRepo — code for the ICDM 2026 demo submission

Cost-effective change localization in software repositories with a temporal
knowledge graph: import structure + co-change relations mined from git
history, queried by training-free personalized propagation on a single CPU.

See `appendix.md` for extended result tables and the consolidated
LocBench leaderboard (Appendix M: small-model lane vs heavyweight lane).

## Layout

- `experiments/chrono.py` — core library: git-plumbing indexing (bare
  clones, per-blob caching), static import layer, temporal co-change layer
  with exponential decay, BM25, grep-style identifier seeds, two-step
  personalized propagation, metrics, leakage-free ancestry cutoffs.
- `experiments/fetch_swebench.py` — SWE-bench Lite/Verified metadata via the
  HF datasets-server API (no heavy deps).
- `experiments/fetch_locbench.py` — Loc-Bench V1 (560 instances) and its
  official `edit_functions` ground truth via the same API.
- `experiments/run_experiments.py` — main E2 runner (issue -> files):
  clones repos, builds graphs per instance strictly before the base commit,
  evaluates the full seed/alpha/lambda grid; resumable.
- `experiments/run_e3.py` — impact-set experiment (leave-last-N-commits-out).
- `experiments/prepare_rerank.py`, `prepare_rerank50.py` — candidate baskets
  (top-20; top-50 union of BM25/grep/graph) with evidence annotations.
- `experiments/run_rerank.py` — single-call LLM rerank over any
  OpenAI-compatible endpoint (`--model`, `--url`, `--conditions`); used for
  Qwen2.5-7B and Claude Sonnet 4.5.
- `experiments/run_f1.py`, `analyze_f1.py` — CodeScout-protocol F1
  (variable-size predictions, threshold tuned on Lite only).
- `experiments/analyze_rerank.py` — strict Acc@k, Wilson CIs, exact McNemar
  (scores against the official `edit_functions` gold).
- `experiments/rescore_official_gt.py` — rescores legacy rerank runs (whose
  input baskets embedded the pre-correction patch-file gold) under the
  official ground truth; see the provenance caveat in `appendix.md`.
- `experiments/analyze_gap.py` — decomposes the gap to SweRank: subgroup
  accuracies, systematic ensemble search (dev/holdout), oracle headroom
  (appendix N).
- `experiments/test_expand.py` — locate-then-expand negative result on
  multi-file fixes.
- `experiments/digest.py`, `make_report.py`, `summarize*.py` — aggregation
  and the HTML results report.
- `experiments/explain_instance.py` — reconstructs and explains a single
  instance's ranking (used for demo material).
- `paper/make_figures.py` — paper figures from the results digest.
- `demo/` — the demo web application: a FastAPI backend that runs
  `chrono.py` in serving mode (index any GitHub repository live, graph and
  timeline, impact set, issue -> files with one optional LLM call) plus a
  Vite/React/sigma.js frontend. See `demo/README.md`; the original
  single-file prototype is kept in `demo/legacy/`.

## Requirements

Python 3.12, git. The experiment pipeline is pure stdlib; `matplotlib` only
for figures; an OpenRouter (or any OpenAI-compatible) key only for the LLM
rerank experiments. The demo app additionally needs `fastapi` + `uvicorn`
(and node once, to build its frontend bundle) — see `demo/README.md`.

## Demo

```bash
python -m venv demo/.venv && demo/.venv/bin/pip install -e demo[test]
cd demo/web && npm install && npm run build && cd ../..
demo/.venv/bin/python -m uvicorn app.main:app --app-dir demo --port 8000
```

## Reproduction sketch

```bash
cd experiments
python fetch_swebench.py lite
python fetch_locbench.py                          # Loc-Bench V1 + official GT
python run_experiments.py                         # E2 on SWE-bench Lite
python run_e3.py                                  # impact set
python prepare_rerank50.py                        # candidate baskets
python run_rerank.py --input data/rerank_input50.jsonl \
  --model qwen/qwen-2.5-7b-instruct --conditions hybrid_plain
python analyze_rerank.py
```

Bare clones (~22 GB for LocBench's 165 repositories) are created on demand
under `experiments/repos/`.
