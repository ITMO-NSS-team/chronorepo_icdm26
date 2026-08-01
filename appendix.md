# ChronoRepo: extended results (online appendix)

Supplementary tables for "ChronoRepo: Cost-Effective Change Localization in
Software Repositories with a Temporal Knowledge Graph" (ICDM 2026 demo track
submission). All numbers below use LocBench's official ground truth (files
of functions edited by the reference patch, the benchmark's `edit_functions`
field), identical to Table 7 of the LocAgent paper (Chen et al., ACL 2025).

## A. Ground-truth correction

Our first evaluation scored rankings against all files touched by the
reference patch, including files *created* by the fix. Such files do not
exist at the issue's base commit and cannot be returned by any retrieval
over the base tree; on instances with 3+ patch files, 59% of patch-file
targets (271/458) are absent from the official ground truth. All numbers
here and in the paper use the official definition. SWE-bench Lite/Verified
experiments are unaffected (self-contained protocol, same gold for all
compared methods).

## B. Main ladder on LocBench (strict file-level Acc@k)

Strict metric: an instance counts only if *all* gold files are in the top-k.
Our run covers 540/560 instances (see D). Wilson 95% CIs for Acc@5.

| Method | Acc@5 | 95% CI | Acc@10 | cost/issue |
|---|---|---|---|---|
| BM25 (ours) | 34.3 | [30.4, 38.4] | 47.0 | ~$0 |
| ChronoRepo graph candidates, no LLM (ours) | 52.6 | [48.4, 56.8] | 58.1 | ~$0 |
| + one vanilla Qwen2.5-7B call, top-20 (ours) | 58.1 | [53.9, 62.2] | 60.9 | <$0.001 |
| + one vanilla Qwen2.5-7B call, top-50 (ours) | 66.1 | [62.0, 70.0] | 70.2 | <$0.001 |
| + one Claude Sonnet 4.5 call, top-50 (ours) | **69.8** | [65.8, 73.5] | **72.8** | ~$0.007 |
| candidate ceiling @50 (all gold present) | 79.6 | — | — | — |
| Agentless, Claude-3.5 (quoted) | 67.5 | — | 67.5 | LLM calls |
| CodeRankEmbed (quoted) | 74.3 | — | 80.9 | GPU embeddings |
| LocAgent, fine-tuned Qwen-7B, agent (quoted) | 78.6 | — | 79.6 | GPU serving |
| LocAgent, Claude-3.5, agent (quoted) | 83.4 | — | 86.1 | ~$0.66 |

Candidate basket for top-50 rows: deduplicated union of three cheap sources
(graph propagation with BM25 seed, graph propagation with grep seed, plain
BM25), 50 candidates. Rerank = one chat call, temperature 0, list of at most
10 paths; unreturned candidates are appended in original order (backfill).

Paired exact McNemar tests (Acc@5): Sonnet vs Qwen top-50: 35/15 discordant,
p = 0.007; each LLM rung vs no-LLM: p < 1e-13; conclusion: widening
candidate coverage (top-20 -> top-50 ceiling 63.3 -> 79.6) buys roughly
twice what model strength buys (+3.7 pts).

## C. Breakdown by number of gold files

Strict Acc@5, official ground truth:

| Method | 1 file (n=467) | 2 files (n=42) | 3+ files (n=31) |
|---|---|---|---|
| BM25, no LLM | 37.7 | 14.3 | 9.7 |
| Graph candidates, no LLM | 57.0 | 31.0 | 16.1 |
| Qwen2.5-7B, top-50 | 71.9 | 38.1 | 16.1 |
| Claude Sonnet 4.5, top-50 | **74.7** | **47.6** | **25.8** |
| candidate ceiling @50 | 82.2 | 64.3 | 61.3 |
| LocAgent ft-7B (bench-wide 78.6, quoted) | 75.3–90.9 ¹ | n/a | n/a |
| LocAgent Claude-3.5 (bench-wide 83.4, quoted) | 80.8–96.4 ¹ | n/a | n/a |

¹ Per-instance LocAgent predictions on LocBench are not public; the interval
is the arithmetic bound on their single-file accuracy implied by the
aggregate and the group shares (86.5 / 7.8 / 5.7%): lower bound if the agent
solves all multi-file instances, upper if none.

Per-file partial credit (share of gold files individually present in
top-10): graph no-LLM 62.3 / 53.6 / 50.0; Qwen 74.9 / 66.7 / 51.0;
Sonnet 76.9 / 67.9 / 57.0. The joint-metric collapse on multi-file
instances is therefore driven by the all-in-top-5 requirement compounding
with a 61.3% ceiling, not by absence of per-file signal.

Related negative result: co-change expansion from a found anchor file does
not recover multi-file companions (oracle anchor's top-10 co-change
neighbours contain only 18% of the missing companions) — companions of
multi-file fixes are largely not evolutionary-coupling partners.

## D. Category and repository-size subgroups (Acc@5, top-50 rerank)

| Category | n | Qwen-7B | Sonnet 4.5 |
|---|---|---|---|
| Bug Report | 230 | 72.2 | 74.8 |
| Feature Request | 145 | 64.1 | 68.3 |
| Performance Issue | 137 | 56.9 | 62.0 |
| Security Vulnerability | 28 | 71.4 | 75.0 |

Bug reports in repositories under ~1,200 files (n=114): both models reach
**78.1%**, the level the fine-tuned LocAgent agent reports benchmark-wide
(78.6). All LocBench bug reports are single-gold-file by construction of
the benchmark.

## E. Exact per-size comparison on SWE-bench Lite

LocAgent released per-instance predictions for Lite (Claude-3.5). Strict
Acc@5 by repository-size quartile, patch-file gold for both sides
(Lite is single-file by construction; our reimplementation of their metric
reproduces their aggregate: 93.7 vs 94.2 published):

| Size quartile | n | LocAgent + Claude-3.5 | Our graph, no LLM |
|---|---|---|---|
| Q1 (<=1153 files) | 76 | 98.7 | 68.4 |
| Q2 (<=1635) | 75 | 93.3 | 68.0 |
| Q3 (<=3175) | 76 | 88.2 | 60.5 |
| Q4 (>3175) | 73 | 94.5 | 69.9 |

## F. Coverage note (540/560)

Twenty LocBench instances are missing from our run: 5 belong to three
repositories whose initial bare clone failed (ccxt/ccxt,
home-assistant/core, roboflow/supervision; transient network failures), and
15 have base commits unreachable from default clone refs (PR-branch
commits); both causes are mechanical, fixed in the current code
(`git fetch origin <sha>` fallback), and a re-run recovering them is in
progress. Missing instances can move Acc@5 by at most ±3.7 points in the
adversarial direction.

## G. Cost summary

One CPU core (Windows 10, 12-core machine, 48 GB RAM, no GPU): median full
pipeline (history mining + both graph layers + 28 ranking variants) 5–7 s
per instance; serving-mode query: milliseconds; incremental update ~3 ms per
commit. Total API spend for every LLM experiment in the paper: ≈ $4.5
(OpenRouter; Qwen2.5-7B-Instruct and Claude Sonnet 4.5, single call per
instance). Claude 3.5 (used by LocAgent) is no longer served by the
provider; Sonnet 4.5 is a stronger substitute, which only reinforces the
finding that model strength is secondary to candidate coverage.
