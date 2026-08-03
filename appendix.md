# ChronoRepo: extended results (online appendix)

> **Headline (latest run).** With the improved candidate recipe (Appendix I)
> plus a single call to a *vanilla, not fine-tuned* Qwen2.5-7B, ChronoRepo
> reaches **76.9% strict Acc@5** on LocBench (n=559, official ground truth),
> statistically indistinguishable from LocAgent's **fine-tuned** 7B agent
> (78.6, multi-turn, GPU-served) and above CodeRankEmbed (74.3) and
> Agentless with Claude-3.5 (67.5). The same pipeline scores 80.0 on
> SWE-bench Lite and 77.0 on Verified. Cost: ~$0.001 per issue, one CPU
> core for the graph.

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
| + one Claude Sonnet 4.5 call, top-50 (ours) | 69.8 | [65.8, 73.5] | 72.8 | ~$0.007 |
| + one vanilla Qwen2.5-7B call, top-100 (ours) | **69.1** | [65.1, 72.8] | **74.4** | <$0.001 |
| candidate ceiling @50 / @100 (all gold present) | 79.6 / **88.3** | — | — | — |
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

## B2. The same ladder on SWE-bench Lite and Verified

Identical pipeline and candidate recipe, gold = files of the reference
patch (both benchmarks are single-file by construction, so the ground-truth
subtlety of Appendix A does not arise). Rerank model: vanilla
Qwen2.5-7B-Instruct, one call, no fine-tuning, no agent loop.

| Method | Lite Acc@5 (n=300) | Verified Acc@5 (n=500) |
|---|---|---|
| BM25, no LLM | 48.3 [42.7, 54.0] | 36.2 [32.1, 40.5] |
| ChronoRepo graph, no LLM | 66.7 [61.2, 71.8] | 54.8 [50.4, 59.1] |
| + one Qwen2.5-7B call over top-50 | **76.7** [71.6, 81.1] | **68.8** [64.6, 72.7] |
| candidate ceiling @50 | 84.0 | 80.4 |
| LocAgent + Claude-3.5 (their released predictions) | 93.7 | n/a |

Acc@10 for the reranked rows: 79.0 (Lite), 72.6 (Verified). Exact McNemar
for the LLM rung against the no-LLM graph ranking: 34/4 discordant on Lite
(p = 6e-7), 78/8 on Verified (p = 2e-15).

Note that the top-50 union and the paper's graph configuration share their
leading candidates, so they coincide at Acc@5/Acc@10; the union only lifts
the ceiling (i.e. what a reranker can reach), which is exactly its purpose.

Cross-benchmark reading: the free graph layer contributes +18.4 (Lite) and
+18.6 (Verified) points over BM25, and a sub-cent LLM call adds another
+10.0 and +14.0. The pattern replicates the LocBench result (+18.3 free,
+13.5 for a cent), so it is not an artifact of one benchmark's
construction.

## B3. Wider baskets and code content (two follow-up experiments)

**Top-100 basket.** Extending the union to 100 candidates raises the
ceiling from 79.6% to **88.3%** — above the LocAgent-with-Claude aggregate
(83.4) — and the same vanilla 7B call converts part of it: 66.1 → 69.1
Acc@5 (exact McNemar 24/8, p = 0.007), matching the frontier-model-on-50
result at a tenth of the cost. Depth of the candidate list remains the
single most productive lever found in this study.

**Code skeletons in the prompt.** Attaching compact code skeletons (first
docstring line + up to 12 class/def signatures, ~500 chars) to the top-20
candidates does not help the vanilla 7B: 64.4 vs 66.1 (p = 0.21; roughly
half of the small deficit is attributable to a slightly weaker basket mix
in this run). Together with the earlier evidence-annotation result, this
suggests single-call small models rank paths well but cannot exploit
in-prompt code context; reading code appears to pay off only inside an
agentic loop or possibly for stronger models (untested).

## B4. Improved candidate recipe: results (LocBench, n=559)

Candidates rebuilt with the recipe of Appendix I; rerank is one call to a
vanilla Qwen2.5-7B, no fine-tuning, no agent loop. Depths are truncations
of the *same* baskets, so the comparison is strictly paired.

| Configuration | ceiling | Acc@5 | 95% CI | Acc@10 | tokens/call |
|---|---|---|---|---|---|
| candidates only, no LLM | — | 67.4 | — | 76.6 | 0 |
| + 7B call, depth 25 | 85.2 | 74.4 | [70.6, 77.9] | 80.5 | 718 |
| **+ 7B call, depth 50** | 91.8 | **76.9** | [73.3, 80.2] | 83.4 | 1,033 |
| + 7B call, depth 100 | 94.3 | 76.4 | [72.7, 79.7] | 83.7 | 1,667 |
| *Agentless, Claude-3.5 (quoted)* | — | 67.5 | — | 67.5 | LLM calls |
| *CodeRankEmbed (quoted)* | — | 74.3 | — | 80.9 | GPU embeddings |
| *LocAgent, fine-tuned 7B agent (quoted)* | — | 78.6 | — | 79.6 | GPU serving |
| *LocAgent, Claude-3.5 agent (quoted)* | — | 83.4 | — | 86.1 | ~$0.66 |

Depth 50 is the operating point: it beats depth 25 (McNemar 24/10,
p = 0.024) and ties depth 100 (10/13, p = 0.68) at 38% fewer tokens.
Coverage past 50 candidates is not convertible by a small model in one
shot, which is the same attention-versus-coverage ceiling seen in the
code-content experiment (B3).

A vanilla 7B over these candidates is statistically level with the
fine-tuned multi-turn agent (76.9 [73.3, 80.2] vs 78.6) and clears both the
GPU-embedding retriever and the Agentless pipeline on Claude-3.5. The
no-LLM candidate order alone (67.4) already matches Agentless.

Per category: bugs 84.2, features 79.3, security 79.3, performance 61.2.
By gold-file count: single-file 83.4 (ceiling 93.2), two files 50.0
(86.4), 3+ files 15.6 (78.1) — multi-file joint localization remains the
hard core for any single-shot ranking.

## B5. Improved recipe on SWE-bench (depth 50, one vanilla 7B call)

| Set | candidates only | + one 7B call | 95% CI | Acc@10 | ceiling@50 |
|---|---|---|---|---|---|
| SWE-bench Lite (n=300) | 72.0 | **80.0** | [75.1, 84.1] | 83.3 | 91.0 |
| SWE-bench Verified (n=500) | 68.8 | **77.0** | [73.1, 80.5] | 83.0 | 92.8 |
| LocBench (n=559) | 67.4 | **76.9** | [73.3, 80.2] | 83.4 | 91.8 |

The LLM rung adds a near-constant +8 to +9.5 points on all three
benchmarks, and the end-to-end figure lands in a narrow 77–80 band, so the
result is a property of the pipeline rather than of one benchmark. For
reference on Lite, LocAgent with Claude-3.5 scores 93.7 under our
reimplementation of their metric (their released per-instance predictions),
so a ~14-point gap to a frontier agent remains there.

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

## F. Coverage note

Final no-LLM grid coverage: **559/560** LocBench instances, zero errors.
The initial run missed 20 (transient clone failures on three large
repositories; 15 base commits from PR branches unreachable from default
clone refs — recovered by a `git fetch origin <sha>` fallback now in
`chrono.py`). On the full 559, strict Acc@5 of the no-LLM rows shifts by
at most +0.9 points versus the 540-instance subset used by the LLM-rerank
rows (whose candidate baskets were prepared before the recovery): BM25
34.3→34.7, grep 34.6→40.1 (grep benefited most from the recovered yt-dlp
instances), graph configs 52.6→53.5.

## G. Does effectiveness depend on the length of project history?

LocBench instances bucketed by the commit count of their repository
(quartiles). Gains are paired within instance; `co-edges` is the median
number of co-change edges available at the instance's base commit.
Reproduce with `experiments/analyze_history_length.py`.

| History (commits) | n | ΔR@10 graph over BM25 | Δ temporal vs static layer | Sonnet-4.5 Acc@5 | median co-edges |
|---|---|---|---|---|---|
| Q1 short (<=4,320) | 136 | +2.3 | −1.2 | 75.7 | 993 |
| Q2 (<=12,593) | 135 | +12.6 | −2.2 | 71.1 | 6,868 |
| Q3 (<=31,224) | 144 | +7.8 | +1.4 | 60.4 | 12,280 |
| Q4 long (>31,224) | 125 | +11.2 | −0.6 | 72.8 | 22,926 |

The dependence is a threshold, not a slope. In young repositories (under
~5k commits, ~1k co-change edges) graph propagation adds almost nothing
over BM25; from Q2 onwards the gain jumps to +8–13 points and then
saturates rather than growing with history size. Saturation follows from
the decay itself: at λ = 1/90 days a one-year-old commit carries weight
0.017, so the method effectively reads only the last one to two years of
activity, and django's two decades confer no advantage over a five-year
project. The flip side is that code untouched for years is invisible to
the temporal layer.

The temporal-vs-static column shows no trend (−2.2 to +1.4, noise): which
single layer wins does not depend on history length; what matters is
having both. Caveat: history-length quartiles are confounded with
repository size and category mix (the Q3 dip mirrors the size-quartile dip
in Appendix E and is a composition artifact), so the defensible claim is
the threshold, not the ordering of buckets.

## I. The improved candidate recipe

Found by an automated sweep over 35 variants (journal:
`notes/NIGHT_LOG.md`; code: `experiments/night_lab.py`). LocBench was split
by instance-id hash: variants were compared on the dev half only, and the
winner was validated once on the untouched holdout half plus Lite and
Verified.

**Recipe.** Reciprocal-rank fusion (k = 40) of six ranked lists:
BM25 over file text; personalized propagation seeded by BM25; personalized
propagation seeded by identifier search; a recency prior (per-file decayed
change count); path-token scores (issue tokens matched against path
segments); and file paths quoted verbatim in the issue text. The raw
identifier-search list is excluded — it is redundant once its propagated
version is present. Test and documentation files are then demoted over the
top-200, and the list is truncated to 100.

**Validation** (no LLM; baseline is the recipe used in the paper):

| Set | ceiling@50 | ceiling@100 | Acc@5 |
|---|---|---|---|
| LocBench holdout (n=296) | 80.1 → **92.2** | 88.5 → **93.2** | 55.7 → **68.2** |
| SWE-bench Lite (n=300) | 83.3 → **91.0** | 90.7 → **95.0** | 66.7 → **72.0** |
| SWE-bench Verified (n=500) | 81.6 → **92.8** | 88.4 → **95.2** | 55.0 → **68.8** |

Holdout gains match dev gains, so the recipe is not overfitted to the
tuning half. Ablation (drop-one on the dev half) ranks the contributions:
path tokens (−10.2 Acc@5 if removed), recency prior (−6.4), test demotion
(−4.5 relative to the fused list), fusion itself (+4.5 ceiling@100 over the
union). Rejected with measurements: RM3 query expansion, a co-change graph
over all file types, PR-transaction grouping of commits, confidence
normalisation of co-change weights, three-step propagation, fusion weights,
deeper source lists, per-directory diversification, and recency re-ranking
of the final list.

## J. Full ablation

Pooled over both LocBench halves (n=559, official ground truth, strict
Acc@5 of the candidate ranking with no LLM; full method 67.4, ceiling@50
91.8). Each row removes or changes one thing; $p$ from exact McNemar
against the full method, with win/loss counts. Reproduce with
`experiments/ablation.py`. The recipe was selected on the dev half only,
and the holdout-only numbers (n=296, in
`results/ablation/ablation_holdout.jsonl`) agree with the pooled ones.

**A. Candidate sources (drop one)**

| Removed | ceiling@50 | Acc@5 | Δ | win/loss | p |
|---|---|---|---|---|---|
| path tokens | 89.6 | 60.3 | −7.2 | 45/5 | <0.0001 |
| graph propagation, both seeds | 91.9 | 64.4 | −3.0 | 37/20 | 0.033 |
| recency prior | 91.1 | 64.8 | −2.7 | 28/13 | 0.028 |
| test/doc demotion | 88.2 | 64.9 | −2.5 | 17/3 | 0.003 |
| paths quoted in the issue | 91.8 | 66.4 | −1.1 | 6/0 | 0.031 |
| raw BM25 list | 91.9 | 66.9 | −0.5 | 16/13 | 0.711 |
| propagation, BM25 seed only | 91.9 | 67.6 | +0.2 | 11/12 | 1.000 |
| propagation, identifier seed only | 91.2 | 67.1 | −0.4 | 13/11 | 0.839 |

**B. Graph layers** (α is the weight of the import layer)

| Configuration | Acc@5 | Δ | p |
|---|---|---|---|
| imports only (α=1) | 67.6 | +0.2 | 1.000 |
| co-change only (α=0) | 67.1 | −0.4 | 0.625 |
| α=0.5 | 67.6 | +0.2 | 1.000 |
| α=0.75 | 68.2 | +0.7 | 0.219 |

**C. Temporal decay**: λ=0 gives 67.1, λ=1/365 gives 67.4, λ=1/30 gives
67.6, against 67.4 at the default λ=1/90 (all p ≥ 0.5).

**D. Propagation**: 1, 2, 3 and 10 iterations all give 67.4–67.6
(all p = 1.0); restart 0.7 gives 67.6, restart 0.3 gives 66.7 (p = 0.29).
A single iteration therefore suffices, which is a 10× compute saving in the
propagation step; the released code keeps 10 iterations because all
reported numbers were produced with it.

**E. Fusion**

| Mechanism | ceiling@50 | Acc@5 | Δ | p |
|---|---|---|---|---|
| fixed-cap union (the earlier recipe) | 86.4 | 57.6 | −9.8 | <0.0001 |
| sum of normalized scores | 92.1 | 66.0 | −1.4 | 0.243 |
| RRF k=20 | 92.3 | 66.2 | −1.3 | 0.189 |
| RRF k=80 | 91.2 | 66.5 | −0.9 | 0.424 |

**Reading.** Six components contribute significantly; the two largest are
the fusion mechanism and the path-token list, both larger than the graph's
own marginal contribution. The redundancy pattern is systematic: any single
source whose signal is also carried by another (raw BM25 under its
propagated version, either propagation seed alone) can be removed for free,
while removing a signal with no substitute (path tokens, both propagations
together, recency) costs accuracy. Every hyper-parameter is inert within
the ranges tested, so the method requires no per-repository tuning.

**On the temporal layer.** The ablation qualifies the motivation honestly.
For issue→file localization the two layers are interchangeable (67.6 vs
67.1), and this holds outside the fusion too: on the full grid the
history-only and import-only configurations score 52.6 and 53.5 strict
Acc@5 (McNemar 11/16, p = 0.44), despite their neighbourhoods overlapping
by a median Jaccard below 0.15. What is not interchangeable is the graph
itself: against plain BM25 it wins 104 instances and loses 0 (p < 1e-30).
The case for the temporal layer specifically rests on two other legs: the
impact-set task, where it beats the static layer 0.577 vs 0.396 R@10, and
cost, since it is mined from commit metadata with no parser and therefore
transfers to any language at no engineering cost.


**End-to-end ablation (through the 7B call, holdout n=296).** Candidate-level
deltas do not transfer uniformly to the final number:

| Configuration | candidates Acc@5 | + 7B Acc@5 | Δ end-to-end | p |
|---|---|---|---|---|
| full | 68.2 | 78.4 | — | — |
| without path tokens | 61.8 | 77.0 | −1.4 | 0.455 |
| without graph propagation | 64.9 | 76.0 | −2.4 | 0.189 |
| fixed-cap union instead of fusion | 59.8 | 73.6 | −4.7 | 0.013 |

The pattern separates two kinds of contribution. Path tokens mostly improve
*ordering*, and a reranker absorbs most of their removal (−7.2 at candidate
level, −1.4 end to end, not significant). Rank fusion mostly improves
*coverage*, lowering the ceiling by 5.4 points when removed, and that loss
is not recoverable by any reranker (−4.7, significant). The practical rule
for pipelines of this shape: spend effort on what enters the basket, not on
how it is ordered inside it.

## H. Cost summary

One CPU core (Windows 10, 12-core machine, 48 GB RAM, no GPU): median full
pipeline (history mining + both graph layers + 28 ranking variants) 5–7 s
per instance; serving-mode query: milliseconds; incremental update ~3 ms per
commit. Total API spend for every LLM experiment in the paper: ≈ $4.5
(OpenRouter; Qwen2.5-7B-Instruct and Claude Sonnet 4.5, single call per
instance). Claude 3.5 (used by LocAgent) is no longer served by the
provider; Sonnet 4.5 is a stronger substitute, which only reinforces the
finding that model strength is secondary to candidate coverage.
