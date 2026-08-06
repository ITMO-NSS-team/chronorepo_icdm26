# ChronoRepo: extended results (online appendix)

> **Headline (latest runs).** With the improved candidate recipe (Appendix
> I) plus a single call to a *vanilla, not fine-tuned* small model,
> ChronoRepo reaches **80.5% strict Acc@5** on LocBench with Qwen3.5-9B
> (n=559, official ground truth) — above LocAgent's **fine-tuned** 7B
> agent (78.6, multi-turn, GPU-served) and SweRank's trained
> SweRankEmbed-Small retriever (80.4). One call to an open-weights MoE
> over a depth-100 basket reaches **83.7 / 88.6**, past the strongest
> published agent's point estimate (83.4) and past SweRank-7B at Acc@10
> (88.4); only SweRank's fully trained pipelines score higher (85.5/86.6
> at Acc@5 — ICLR 2026). The 7B rung of the paper (76.9) and the SWE-bench
> results (80.0 Lite / 77.0 Verified) are unchanged. Cost: $0.0002–0.002
> per issue, one CPU core for the graph. Appendix M has the consolidated
> leaderboard; N.4–N.5 the follow-up runs.

Supplementary tables for "ChronoRepo: Cost-Effective Change Localization in
Software Repositories with a Temporal Knowledge Graph" (ICDM 2026 demo track
submission). Unless a section notes otherwise, numbers use LocBench's
official ground truth (files of functions edited by the reference patch,
the benchmark's `edit_functions` field), identical to Table 7 of the
LocAgent paper (Chen et al., ACL 2025). **Provenance, verified:** the
legacy basket files (`rerank_input*.jsonl`) embed the pre-correction
patch-file gold, but every ladder number in Appendices B–B3 was scored
against the official definition — reproduced exactly by
`experiments/rescore_official_gt.py` (protocol and outputs:
`results/summary_rescore_gt.md`). Everything the paper reports
(Appendices B4, B5, J, L) uses the official ground truth throughout.

## A. Ground-truth correction

Our first evaluation scored rankings against all files touched by the
reference patch, including files *created* by the fix. Such files do not
exist at the issue's base commit and cannot be returned by any retrieval
over the base tree; on instances with 3+ patch files, 59% of patch-file
targets (271/458) are absent from the official ground truth. All numbers
here and in the paper use the official definition. SWE-bench Lite/Verified
experiments are unaffected (self-contained protocol, same gold for all
compared methods).

## B. Legacy ladder on LocBench (strict file-level Acc@k)

Strict metric: an instance counts only if *all* gold files are in the top-k.
Our run covers 540/560 instances (see F). Wilson 95% CIs for Acc@5.
*Historical section:* these rows predate the recipe optimization (Appendix
I); the operative numbers are in B4–B5 and L. All rows below are
official-GT — verified by rerunning
`experiments/rescore_official_gt.py` against `edit_functions.json`, which
reproduces every accuracy, ceiling and paired test exactly
(`results/summary_rescore_gt.md`).

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
patch. SWE-bench Lite is single-file by construction (300/300 one-file
patches); Verified is mostly single-file (429/500; 71 instances touch 2–21
files, and the two with more than five gold files cap strict Acc@5 at
99.6). Files *created* by the fix — the ground-truth subtlety of Appendix
A — are essentially absent here (0 patches in Lite, 1/500 in Verified), so
patch-file gold is sound on both sets. Rerank model: vanilla
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
| *CodeRankEmbed 137M (quoted)* | — | 74.3 | — | 80.9 | GPU embeddings |
| *SweRankEmbed-Small 137M (quoted)* | — | 80.4 | — | 84.8 | GPU embeddings |
| *LocAgent, fine-tuned 7B agent (quoted)* | — | 78.6 | — | 79.6 | GPU serving |
| *SweRank, trained 7B retrieve+rerank (quoted)* | — | 85.5 | — | 88.4 | GPU serving |
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

Strict Acc@5, official ground truth. Computed on the 540-instance subset of
Appendix F (the full 559-instance set has 32 instances with 3+ gold files;
the paper cites that count):

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
multi-file fixes are largely not evolutionary-coupling partners. *Caveat:*
this experiment (`test_expand.py`) selected its 3+-file instances and
companions under the pre-correction patch-file gold, where 59% of
multi-file targets do not exist at the base commit and are unfindable by
construction; 18% is therefore a lower bound, and the experiment should be
rerun on `edit_functions` gold before the claim is leaned on.

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
Reproduce with `experiments/analyze_history_length.py`. Ground-truth note:
the ΔR@10 columns are computed from the original grid run
(`results_locbench.jsonl`, patch-file gold), while the Sonnet Acc@5 column
is rescored under the official `edit_functions` gold; since the Δ columns
are within-instance *differences* between methods, the bucket ordering is
unaffected, but absolute Δ values would shift slightly under the official
definition.

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

## K. Material moved here from the paper

The demo track allows four pages; the following content was cut from the
submission for space and is preserved here in full.

### K.1 System architecture

Indexing is a single pass of `git log --numstat` over a bare clone
(commits touching more than 30 files are dropped as bulk edits), followed
by batched `cat-file` retrieval of the blobs of the target revision, parsed
into import edges. Results are cached per blob hash, so re-indexing after a
commit re-parses only changed blobs. Both graph layers live in memory as
row-normalized sparse adjacency, a few MB per repository:
a static layer `S` (importer to imported) and a temporal layer `T` (files
co-changed in a commit, weight `sum exp(-lambda * age)`). Queries run
personalized PageRank over `alpha*S + (1-alpha)*T` from a seed
distribution, and the resulting ranking is fused with the lexical, path and
recency lists (Appendix I). The web UI exposes three views over the same
index: graph timeline, impact set, and issue-to-files.

### K.2 Layer orthogonality figure

For every file we compared its top-10 neighbours in the static versus the
temporal layer. Median Jaccard overlap is below 0.15 on 9 of 12 projects
(scikit-learn and matplotlib 0.00, django 0.07, sympy 0.08, xarray 0.13,
flask 0.23, seaborn 0.25, requests 0.33). The layers therefore encode
substantially different relations, which motivated mixing them; the
ablation (Appendix J) shows the mixture is nonetheless not better than
either layer alone for issue-to-file localization, while the temporal layer
dominates for the impact-set task. The figure is reproducible with
`paper/make_figures.py`.

### K.3 Per-category figure (LocBench)

R@10 of the graph configuration against BM25, by issue category:
bugs 0.513 -> 0.617 (+10.4), features 0.476 -> 0.598 (+12.2), performance
0.489 -> 0.590 (+10.0), security 0.491 -> 0.698 (+20.7). The security gain
is the largest, which is the opposite of what the first (patch-file) ground
truth suggested, and is explained by Appendix A: security fixes often add
files, and those are not localization targets under the official ground
truth.

### K.4 Evaluation under the CodeScout F1 protocol

CodeScout evaluates file localization on SWE-bench Verified with
variable-size prediction sets and macro F1. We adopted their protocol
unchanged: the prediction set is every file scoring at least
`theta * max`, capped at 5, with `theta` selected on Lite only and applied
blind to Verified.

| Method | Precision | Recall | F1 |
|---|---|---|---|
| BM25 with the same thresholding (ours) | 17.2 | 25.4 | 18.8 |
| ChronoRepo, no LLM (ours) | 32.6 | 44.6 | **35.2** |
| Agentless + Qwen2.5-32B (quoted) | 25.6 | 78.9 | 35.4 |
| LocAgent + Qwen2.5-32B (quoted) | 34.2 | 79.4 | 44.2 |
| CodeScout-1.7B (quoted) | 58.4 | 54.3 | 55.5 |
| CodeScout-14B (quoted) | 71.0 | 68.7 | 68.6 |
| Claude-Sonnet-4.5, best scaffold (quoted) | 84.5 | 82.9 | 82.0 |

A training-free CPU pipeline is level with the Agentless pipeline driving a
32B model (35.2 vs 35.4) at zero inference cost, with a much better
precision/recall balance, but well short of RL-trained search agents. This
was run before the improved candidate recipe; the hypothesis that the
method would match an RL-trained 1.7B model under this protocol was
therefore rejected, and we record it as such.

## L. Which model to put in the single call

### L.0 Master table: full-run results

One prompt, identical candidate baskets (final recipe, top 50), all 559
LocBench instances, official ground truth, strict Acc@k. Costs are per
1,000 issues, computed from measured token usage at OpenRouter prices.
Ten further models were eliminated at an 80-instance screening stage
(Qwen3-235B, Kimi-K2.7-Code, GLM-5.2, DeepSeek-chat-v3.1, Llama-3.3-70B,
Qwen3-32B, Qwen3-Coder-Next, Qwen2.5-72B, Qwen3-Next-80B, Qwen3-235B
thinking); their screening scores remain in the tables below.

| Model | Architecture | Acc@5 [95% CI] | Acc@10 | $/1000 issues |
|---|---|---|---|---|
| GLM-5.1 | MoE | **82.8** [79.5, 85.7] | 86.9 | $2.20 |
| Kimi K2-0905 | MoE 1T-A32B | **82.8** [79.5, 85.7] | 86.6 | $0.90 |
| Kimi K3 | MoE 1T, reasoning | **81.9** [78.5, 84.9] | 86.2 | $12 |
| DeepSeek V4 Pro | MoE, reasoning | **81.2** [77.8, 84.2] | 85.3 | $1.20 |
| Qwen3-Coder | MoE 480B-A35B | **81.0** [77.6, 84.1] | 86.4 | $0.50 |
| DeepSeek V4 Flash | MoE | **80.9** [77.4, 83.9] | 86.0 | $0.30 |
| MiniMax-M2.7 | MoE | **80.9** [77.4, 83.9] | 85.3 | $0.90 |
| GLM-4.7 | MoE | **80.1** [76.6, 83.2] | 84.8 | $3.00 |
| Qwen2.5-7B-Instruct | dense 7B | **76.9** [73.3, 80.2] | 83.4 | $0.10 |
| *LocAgent + Claude-3.5 agent (quoted)* | *proprietary* | *83.4* | *86.1* | *~$660* |
| *LocAgent + fine-tuned 7B agent (quoted)* | *fine-tuned* | *78.6* | *79.6* | *GPU* |
| *Our candidates, no LLM* | *graph+fusion, CPU* | *67.4* | *76.6* | *~$0* |

Three regularities across the table. First, the leaders are large
code-heavy MoE models; dense models up to 72B do not beat a dense 7B.
Second, every reasoning-biased entry (thinking Qwen, DeepSeek V4 Pro,
Kimi K3, GLM-4.7 by token count) lands below the best non-reasoning model
of its family while spending 1.5 to 3 times the tokens. Third, price and
quality are uncorrelated in this range: the two co-leaders cost $0.0009 and
$0.0022 per issue while the most expensive entry ($0.0121) trails them.



All models rerank the *same* candidate baskets (final recipe, top 50), one
call, temperature 0, no agent loop. Stage 1 screens on a fixed random
subset of 80 LocBench instances; the two leaders were then run on all 559.
Reproduce with `experiments/model_bakeoff.py`.

**Stage 1 (n=80, strict Acc@5)**

| Model | open weights | Acc@5 | 95% CI |
|---|---|---|---|
| Qwen3-Coder (480B-A35B) | yes | 82.5 | [72.7, 89.3] |
| Kimi K2-0905 (1T-A32B) | yes | 82.5 | [72.7, 89.3] |
| Qwen3-235B-A22B-2507 | yes | 81.2 | [71.3, 88.3] |
| Qwen2.5-7B-Instruct | yes | 77.5 | [67.2, 85.3] |
| Llama-3.3-70B-Instruct | yes | 76.2 | [65.9, 84.2] |
| Qwen3-Next-80B-A3B | yes | 75.0 | [64.5, 83.2] |
| Qwen2.5-72B-Instruct | yes | 75.0 | [64.5, 83.2] |
| DeepSeek-chat-v3.1 | yes | 77.5 | [67.2, 85.3] |
| Qwen3-32B | yes | 76.2 | [65.9, 84.2] |
| Qwen3-235B-A22B **thinking** | yes | 71.2 | [60.5, 80.0] |

The thinking variant is the clearest negative result of the bake-off: ten
points below its own non-thinking sibling (81.2) while spending 3284 tokens
per call against 1057. Extended deliberation actively hurts a task that,
given good candidates, is recognition rather than reasoning.

**Full LocBench (n=559, strict)**

| Model | Acc@5 | 95% CI | Acc@10 | mean tokens |
|---|---|---|---|---|
| Kimi K2-0905 | **82.8** | [79.5, 85.7] | 86.6 | 988 |
| GLM-5.1 | **82.8** | [79.5, 85.7] | **86.9** | 1303 |
| Kimi K3 | 81.9 | [78.5, 84.9] | 86.2 | 1484 |
| DeepSeek V4 Pro | 81.2 | [77.8, 84.2] | 85.3 | 1802 |
| Qwen3-Coder (480B-A35B) | 81.0 | [77.6, 84.1] | 86.4 | 1082 |
| MiniMax-M2.7 | 80.9 | [77.4, 83.9] | 85.3 | 1491 |
| DeepSeek V4 Flash | 80.9 | [77.4, 83.9] | 86.0 | 1495 |
| GLM-4.7 | 80.1 | [76.6, 83.2] | 84.8 | 2347 |
| Qwen2.5-7B | 76.9 | [73.3, 80.2] | 83.4 | 1033 |
| *LocAgent + Claude-3.5 agent (quoted)* | *83.4* | — | *86.1* | multi-turn |
| *LocAgent + fine-tuned 7B agent (quoted)* | *78.6* | — | *79.6* | multi-turn |

No open model in the pool exceeds 83.4 at Acc@5 on its own. Two of them,
Kimi K2 and GLM-5.1, tie it (their 95% CI covers the target) and exceed it
at Acc@10. Note the regression from
screening to full evaluation: four models were tied at 82.5 on the
80-instance subset, but on all 559 they spread over 80.1 to 82.8, so
subset screening ranks candidates but does not settle differences of a few
points.

**Ensembling: mostly no, once yes.** Reciprocal-rank fusion of the Kimi and
Qwen3-Coder outputs gives 82.3 at Acc@5, *below* Kimi alone (82.8); adding
the 7B or the candidate order lowers it further to 81.0 and 79.2. Fusing
the two co-leaders with Qwen3-Coder reaches 83.4, exactly the LocAgent
figure, at 87.3 Acc@10. We flag that last number as weak evidence: the
configuration was chosen after seeing results on the same 559 instances,
among roughly five fusions tried, and the spread between them sits inside
the noise band. The robust claims are the single-model ones. At Acc@10
fusion helps consistently (87.3 to 87.8 against 86.1 for the agent), which
is the configuration to use when a shortlist of ten is acceptable.

The two co-leaders agree on the top-ranked file in 86.2% of instances, so
their errors are largely shared, which is why fusion buys little. DeepSeek
V4 Pro spends 1802 tokens per call, nearly double the leaders, and lands
1.6 points lower: a fourth data point for deliberation not paying off on
this task. Kimi K3 is the fifth and the most expensive one: at 14 times the
per-call price of K2 and 1.5 times the tokens, it scores 81.9 against K2's
82.8 (McNemar 7/12, p = 0.36) — the newer flagship with a reasoning bias
does not beat its own cheaper predecessor here.

Exact McNemar against the 7B: Kimi 40/7 (p < 1e-4), Qwen3-Coder 35/12
(p = 0.001). Kimi versus Qwen3-Coder: 20/10, p = 0.099, not significant.

**Reading.** An open-weights model in a single call reaches 82.8 against
83.4 for the best published agent, a difference well inside our confidence
interval, and exceeds it at Acc@10 (86.6 vs 86.1). Cost per issue is under
$0.003 against roughly $0.66, and there is no agent loop, no fine-tuning
and no GPU on our side beyond whatever serves the model.

Size alone does not predict quality here: Qwen2.5-72B and Qwen3-Next-80B
both scored below the 7B, while the two large code-oriented mixture-of-
experts models led. With good candidates the task is closer to recognition
than to reasoning, which is consistent with the code-content and evidence
ablations (B3) showing that extra context does not help small models.

Practical failures encountered: `deepseek/deepseek-v3.1` is not a valid
OpenRouter id (400 on every call; the served ids are
`deepseek-chat-v3.1` and `deepseek-v3.1-terminus`), and thinking models
such as Qwen3-32B return `content: null` with the answer in a separate
`reasoning` field and need a larger token budget. Both are handled in the
current `run_rerank.py`.

## H. Cost summary

One CPU core (Windows 10, 12-core machine, 48 GB RAM, no GPU): median full
pipeline (history mining + both graph layers + 28 ranking variants) 5–7 s
per instance; serving-mode query: milliseconds; incremental update ~3 ms per
commit. Total API spend for every LLM experiment in the paper: ≈ $4.5
(OpenRouter; Qwen2.5-7B-Instruct and Claude Sonnet 4.5, single call per
instance). Claude 3.5 (used by LocAgent) is no longer served by the
provider; Sonnet 4.5 is a stronger substitute, which only reinforces the
finding that model strength is secondary to candidate coverage.

## M. Consolidated LocBench leaderboard (file-level, strict Acc@k)

All rows: Loc-Bench V1 (560 instances), official `edit_functions` ground
truth, strict metric (*all* gold files in top-k). Published rows are quoted
from Table 7 of LocAgent (ACL 2025) and Table 2 of SweRank (ICLR 2026); our
rows cover 559/560 instances. Costs marked † come from the papers' own cost
studies (LocAgent's was run in the SWE-bench Lite setting; no per-issue
LocBench costs are published) and exclude standing GPU-serving cost.

### M.1 Small-model lane (no component above 9B)

| # | System | Trained? | Acc@5 | Acc@10 | $/issue | Hardware |
|---|---|---|---|---|---|---|
| 1 | **SweRank 7B retrieve+rerank** (SweRankLLM-Small, quoted) | yes (both stages) | **85.5** | **88.4** | ≈$0.01† | GPU |
| 2 | **ChronoRepo + one vanilla Qwen3.5-9B call (ours)** | **no** | 80.5 | 85.5 | <$0.001 | CPU + API |
| 3 | SweRankEmbed-Small 137M retriever (quoted) | yes | 80.4 | 84.8 | — | GPU |
| 4 | LocAgent agent, fine-tuned Qwen2.5-7B (quoted) | yes (SFT) | 78.6 | 79.6 | ≈$0.05† | GPU |
| 5 | ChronoRepo + one vanilla Qwen2.5-7B call (ours) | no | 76.9 | 83.4 | <$0.001 | CPU + API |
| 6 | CodeRankEmbed 137M retriever (quoted) | yes | 74.3 | 80.9 | — | GPU |
| 7 | ChronoRepo candidates, no LLM (ours) | no | 67.4 | 76.6 | ~$0 | CPU |
| 8 | BM25 (ours) | no | 34.7 | 48.1 | ~$0 | CPU |

Reading: every system above our 9B row is *trained for the task* — and
only one remains: the fully trained SweRankLLM pipeline. An untrained 9B
call now clears the fine-tuned multi-turn agent (80.5 vs 78.6) and the
trained SweRankEmbed retriever (80.4) at a fraction of their cost;
SweRank holds the lane ceiling at 10–15× our per-issue price plus GPU
serving (N.5).

### M.2 Heavyweight lane (frontier agents, 32B rerankers, large MoE)

| # | System | Loop | Acc@5 | Acc@10 | $/issue |
|---|---|---|---|---|---|
| 1 | **SweRankLLM-Large, trained 32B reranker** (quoted) | single pass | **86.6** | **89.8** | GPU |
| 2 | **ChronoRepo + one Kimi-K2 call, depth 100 (ours)** | one call | 83.7 | **88.6** | <$0.002 |
| 3 | LocAgent agent, Claude-3.5 (quoted) | multi-turn | 83.4 | 86.1 | ≈$0.66† |
| 4 | ChronoRepo + one Kimi-K2 / GLM-5.1 call, d50 (ours) | one call | 82.8 | 86.6 / 86.9 | <$0.003 |
| 5 | ChronoRepo + one Qwen3-Coder call (ours) | one call | 81.0 | 86.4 | ≈$0.001 |
| 6 | OpenHands agent, Claude-3.5 (quoted) | multi-turn | 79.8 | 80.0 | ≈$0.79† |
| 7 | SWE-agent, Claude-3.5 (quoted) | multi-turn | 77.7 | 77.7 | ≈$0.67† |
| 8 | Agentless, Claude-3.5 (quoted) | pipeline | 67.5 | 67.5 | LLM calls |

At Acc@10 the depth-100 MoE call (88.6) passes every published agent and
SweRank-7B (88.4), 1.2 short of the trained 32B ceiling; at Acc@5 it
passes the strongest agent's point estimate (83.7 vs 83.4) with the
1.8-point gap to SweRank concentrated in multi-file instances (N.4).

### M.3 Entries not directly comparable (excluded from the ladder)

- **GraphLocator** (arXiv 2512.22469) evaluates on Loc-Bench but reports
  Success-Location/Recall/Precision (file-level SL 84.97) rather than
  strict Acc@k.
- **LARGER** (arXiv 2605.16352) reports 87.0–89.1 file Acc@5 on Loc-Bench
  with a GPT-5.2 backbone and re-runs all baselines under different
  backbones (its LocAgent reproduction scores 65.3), so its numbers are
  not comparable to this table's quoted rows.
- **MULocBench** (arXiv 2509.25242) documents ten Loc-Bench instances with
  questionable ground truth and shows all published localizers drop
  sharply on a broader issue mix — a standing caveat on every row above.

## N. Where the gap to SweRank lives

SweRank-7B (85.5 / 88.4, trained retriever + trained reranker) is the
nearest system above our best single call (Kimi-K2 / GLM-5.1, 82.8 /
86.6–86.9). This appendix decomposes the 2.7-point gap using the
per-instance outputs of all nine full-run models. Reproduce with
`experiments/analyze_gap.py`.

### N.1 Subgroups (strict Acc@5, n=559, official GT)

| Subgroup | n | Kimi-K2 | GLM-5.1 | Qwen3-Coder | Qwen2.5-7B |
|---|---|---|---|---|---|
| all | 559 | 82.8 | 82.8 | 81.0 | 76.9 |
| **gold = 1 file** | 483 | **88.0** | **88.2** | **86.3** | 83.4 |
| gold = 2 files | 44 | 59.1 | 59.1 | 61.4 | 50.0 |
| gold ≥ 3 files | 32 | 37.5 | 34.4 | 28.1 | 15.6 |
| Bug Report | 241 | **88.0** | **88.4** | 84.6 | 84.2 |
| Feature Request | 150 | 84.7 | 84.7 | 84.0 | 79.3 |
| Performance Issue | 139 | 71.9 | 71.9 | 71.2 | 61.2 |
| Security Vulnerability | 29 | 82.8 | 79.3 | 82.8 | 79.3 |
| issue quotes a .py path | 238 | **87.0** | **87.4** | 85.3 | 84.0 |
| gold=1 & repo ≤ ~950 files | 220 | **92.7** | **92.7** | **91.4** | **88.2** |

Bold: at or above SweRank-7B's benchmark-wide 85.5. On single-gold-file
instances — 86.4% of the benchmark — one MoE call scores 88.0–88.2 Acc@5
and 90.1–90.3 Acc@10, above SweRank-7B's *aggregate* (85.5 / 88.4), and
the vanilla 7B reaches 83.4, the level of the Claude-3.5 agent's
aggregate. Caveat as in Appendix C: SweRank's per-instance predictions are
not public, so its own single-file accuracy is unknown (presumably also
above its aggregate); the honest statement is that *our single-file
performance exceeds their benchmark-wide number*, not that we beat them
head-to-head on the slice. The converse decomposition: if multi-file
instances converted at the single-file rate, the aggregate would be ≈88.0
— the entire gap to SweRank (and beyond) sits in 76 multi-file instances
at 50.0 Acc@5 (ceiling 82.9) plus the Performance category, whose deficit
is conversion, not coverage (ceiling 89.2, Kimi 71.9).

### N.2 Ensembling the nine models is a dead end (negative result)

Systematic search over all 2–4-model combinations × {RRF k=60, top-5
voting}, selected on the dev half and evaluated on the untouched holdout:
the dev-best ensemble (top-5 voting) reaches **83.5 full-set Acc@5** —
+0.7 over the best single model, still 2.0 below SweRank-7B. The oracle
that picks the best of all nine models per instance reaches only 86.8, so
even perfect routing barely clears 85.5: the nine models share their
errors, and no amount of single-call ensembling closes the gap. This
supersedes and confirms the ad-hoc fusion result of Appendix L.

### N.3 Headroom anatomy and the two levers

Of 559 instances, 46 are basket misses (gold not in the top-50 candidates;
33 of them single-gold-file) and 28 are convertible-but-unconverted (gold
in basket, all nine models fail). The two corresponding levers:

1. **Multi-file conversion** (76 instances at 50.0): count-aware
   prompting (ask the model to first decide how many files the fix spans),
   self-consistency voting over ~5 sampled calls, or anchor-plus-
   companions prompting. Converting multi-file at the single-file rate is
   worth ≈ +5.2 points — more than the whole gap.
2. **Basket recall on single-file misses** (33 instances): depth-100
   baskets (ceiling 94.3 vs 91.8) reranked by an MoE rather than the 7B —
   the 7B could not convert depth 100 (Appendix B4), but the stronger
   models were never tried on it.

Both experiments are single-call, OpenRouter-priced at roughly $1–2 for
the full benchmark per configuration.

### N.4 The levers, tested (follow-up runs, 2026-08-04)

All runs: same baskets (`rerank_final_locbench.jsonl`), one call,
temperature 0 unless stated, n=559, official GT, McNemar against the
Kimi-K2 depth-50 baseline (82.8 / 86.6).

| Configuration | Acc@5 | Acc@10 | vs base (McNemar) | gold=1 | gold≥2 |
|---|---|---|---|---|---|
| **Kimi-K2, depth 100** | **83.7** | **88.6** | @5: 14/9, p=0.40; @10: 17/6, **p=0.035** | 90.1 | 43.4 |
| GLM-5.1, depth 100 | 83.2 | 88.4 | 14/12, p=0.85 | 88.8 | 47.4 |
| Kimi-K2, count-aware prompt, d50 | 82.1 | 86.6 | 8/12, p=0.50 | 88.0 | 44.7 |
| Kimi-K2, self-consistency 5×t=0.7, vote | 82.8 | 86.4 | 7/7, p=1.00 | 88.6 | 46.1 |

**Depth 100 works — for the MoE.** The lever the 7B could not use
(Appendix B4: 76.4 at depth 100) the MoE can: +2.0 points of Acc@10
(significant), reaching **88.6 — past SweRank-7B's benchmark-wide 88.4 —
with a single untrained call**, and 90.1 on the single-file slice. Acc@5
gains +0.9 (not significant). Token cost rises 988→1,651 per call
(≈$1.5/1,000 issues, still ~1/440 of the LocAgent-Claude agent). GLM-5.1
replicates the pattern (83.2/88.4). The oracle over both depth-100 runs
reaches only 85.3 Acc@5 — their errors, again, are shared.

**The multi-file levers fail.** A count-aware prompt (decide the size of
the fix first) moves nothing overall and does not lift gold≥2 (44.7 vs
50.0, n=76, noise). Five-sample self-consistency voting is *exactly* the
greedy run (82.8, 7/7 discordant): the individual samples span 81.6–82.8
and their union-vote recovers nothing, i.e. the errors are systematic,
not stochastic. Together with the ensemble result (N.2) this closes the
book on single-call variance tricks: the residual Acc@5 gap to SweRank
(83.7 vs 85.5, ≈10 instances) lives in multi-file fixes and appears to
require either training or machinery beyond one-shot ranking.

### N.5 Modern small models: the 7B-lane headline moves to 9B

Same protocol as the bake-off (depth 50, one call, temperature 0):

| Model | Acc@5 | 95% CI | Acc@10 | gold=1 | $/1k issues |
|---|---|---|---|---|---|
| **Qwen3.5-9B** | **80.5** | [77.0, 83.6] | **85.5** | 86.7 | ≈$0.16 |
| Qwen3-8B | 76.9 | [73.3, 80.2] | 82.6 | 84.5 | ≈$0.25 |
| Qwen2.5-7B (paper baseline) | 76.9 | [73.3, 80.2] | 83.4 | 83.4 | ≈$0.10 |
| Ministral-8B-2512 | 74.1 | [70.3, 77.5] | 82.8 | 81.2 | ≈$0.15 |
| Granite-4.1-8B | 74.2 | [70.5, 77.7] | 80.9 | 80.7 | ≈$0.15 |

Qwen3.5-9B beats the Qwen2.5-7B baseline by 3.6 points at the same price
class (paired McNemar 33/13, **p=0.0045**) and, untrained, clears the
fine-tuned multi-turn LocAgent-7B agent (78.6) and matches
SweRankEmbed-Small (80.4); within the small lane only the fully trained
SweRankLLM pipeline (85.5) remains ahead. Its single-file-slice accuracy
(86.7) exceeds SweRank-7B's benchmark-wide aggregate. Depth 100 under the
9B gives 81.0/86.0 (+0.5, n.s.) — the depth lever scales with model
strength. The other modern small models do not beat the old 7B, so the
generational gain is model-specific, not universal.

### N.6 Prompt optimization does not move the small models

Five system-prompt variants, all staying in the ordering/format register
(content additions were already ruled out in B3): `top1` (name the single
most likely file first, then complete the list), `exact10` (return exactly
ten paths rather than "up to ten"), `verbatim` (copy paths exactly as
given), `fewshot` (one worked example), `cat` (supply the benchmark's
issue category and how it should weigh candidates). Compared on the
LocBench **dev half only**, same hash split as the recipe sweep; strict
Acc@5, exact McNemar against the default prompt on identical instances.
Reproduce with `experiments/analyze_prompts.py`.

| Prompt | Qwen3.5-9B (dev) | vs def. | Qwen2.5-7B (dev) | vs def. |
|---|---|---|---|---|
| default | 79.5 | — | 75.3 | — |
| verbatim | 80.6 | 4/1, p=0.38 | 75.3 | 2/2, p=1.00 |
| cat | 80.6 | 4/1, p=0.38 | 74.5 | 3/5, p=0.73 |
| top1 | 79.8 | 3/2, p=1.00 | 74.5 | 2/4, p=0.69 |
| fewshot | 79.8 | 3/2, p=1.00 | 74.1 | 2/5, p=0.45 |
| exact10 | 79.1 | 4/5, p=1.00 | **71.9** | 5/14, p=0.064 |

Nothing helps. The largest dev movement (+1.1 for the 9B) rests on four
instances, and **neither dev leader replicates on the untouched holdout**
(n=296): default 81.4, `cat` 81.8 (4/3, p=1.00), `verbatim` 80.4 (3/6,
p=0.51). Requiring exactly ten paths actively hurts the 7B (−3.4): it
pads the list and pushes correct files out of the top five. Supplying the
issue category does not repair the Performance-category deficit either.

Together with B3 (skeletons, evidence annotations), N.4 (count-aware
prompting, self-consistency) and N.2 (ensembles), this is the fifth
independent attempt to extract more from a fixed candidate set by
changing what the model is asked or how often it is asked, and the fifth
null result. The levers that did move the metric were structural: the
candidate recipe (+10.8), basket depth under a strong enough model (+2.0
Acc@10) and model generation (+3.6 from 7B to 9B). For this task, given
good candidates, prompt surface is not where the accuracy lives.

## O. Multi-step schemes for small models (negative result)

Following N.4's conclusion that single-call variance tricks are exhausted,
we tested whether *multi-call composition* closes the gap to SweRank-7B
(85.5): chunk cascades (4x25 -> playoff), sliding windows (bottom-up with
carry, RankGPT-style), two-pass split reranking (1-50 and 51-100 with a
playoff), iterative refinement, and anchor-plus-companions two-step
prompting for multi-file fixes. Dev half for iteration, holdout untouched,
pooled n=559 for the final verdict. Reproduce with
`experiments/night2_lab.py`; full journal in `notes/NIGHT2_LOG.md`.

**Qwen3.5-9B (dev, n=263):** best scheme (sliding window) scores 81.4
against 81.0 for a single depth-100 call — McNemar 4/3, p=1.0 — at three
times the tokens. Cascades and anchor prompting actively hurt multi-file
instances (28.6 and 37.1 vs 42.9 at base): chunking severs the joint
context between candidate files, and anchoring imposes a single-file
hypothesis exactly where a group must be recognised.

**Strict Qwen2.5-7B (pooled n=559):** the one glimmer — solo depth-100
hurts the 7B (75.7 < 76.0 on dev), while windowed depth-100 recovers it:
77.8 [74.2, 81.1] vs 76.9 for the single call. Direction consistent across
two independent schemes, but not significant (Acc@5 McNemar 17/12,
p=0.46; Acc@10 14/7, p=0.19) and worth at most one point at 2.5x the
cost.

**Conclusion.** With Appendix N this closes the composition space for
untrained small models: ensembles, voting, prompt variants, in-context
code, depth scaling, and now multi-call scheduling all fail to move
strict Acc@5 materially. The residual gap between the best untrained
small-model configuration (81.0) and SweRank-7B (85.5) is the measured
value of task-specific training, not of orchestration.
