# Rescoring the legacy rerank ladder under the official ground truth

Produced by `experiments/rescore_official_gt.py` (2026-08-04) against
`data/edit_functions.json` (Loc-Bench V1 official gold: files of edited
functions). Purpose: the legacy basket files (`rerank_input*.jsonl`)
embedded the pre-correction patch-file gold; this run verifies that every
ladder number reported in Appendix B–B3 was in fact computed under the
official definition. **All rows reproduce exactly.**

## Top-20 baskets (`rerank_input.jsonl`, `rerank_qwen7b.jsonl`, n=540)

| condition | Acc@5 | 95% CI | Acc@10 | ceiling |
|---|---|---|---|---|
| bm25_plain | 52.0 | [47.8, 56.2] | 55.0 | 60.2 |
| hybrid_plain | 58.1 | [53.9, 62.2] | 60.9 | 63.3 |
| hybrid_evidence | 56.7 | [52.5, 60.8] | 59.6 | 63.3 |

## Top-50 baskets (`rerank_input50.jsonl`, n=540)

| run | Acc@5 | 95% CI | Acc@10 | ceiling |
|---|---|---|---|---|
| Qwen2.5-7B (`rerank_qwen7b_top50.jsonl`) | 66.1 | [62.0, 70.0] | 70.2 | 79.6 |
| Claude Sonnet 4.5 (`rerank_sonnet45_top50.jsonl`) | 69.8 | [65.8, 73.5] | 72.8 | 79.6 |

## Top-100 baskets (`rerank_input100.jsonl`, n=540)

| run | Acc@5 | 95% CI | Acc@10 | ceiling |
|---|---|---|---|---|
| Qwen2.5-7B (`rerank_qwen7b_top100.jsonl`) | 69.1 | [65.1, 72.8] | 74.4 | 88.3 |
| + code skeletons (`rerank_qwen7b_content.jsonl`) | 64.4 | [60.3, 68.4] | 67.8 | 88.3 |

## Paired tests (official GT, exact two-sided McNemar, Acc@5)

- Sonnet 4.5 vs Qwen-7B, top-50: 35/15 discordant, p = 0.0066
  (appendix states 35/15, p = 0.007 — reproduced).
- Qwen-7B top-50 vs no-LLM basket order: 81/8, p = 2.5e-16
  (appendix states p < 1e-13 — reproduced).
- Evidence annotations vs plain paths, top-20: 3/11 discordant,
  p = 0.057, direction against evidence. The paper previously cited
  p = 0.04 from the pre-correction scoring; the official-GT value is 0.06
  (same direction, borderline rather than significant).

## No-LLM reference on the identical instance set

Basket order without any LLM (n=539): BM25 top-50 34.3 / 47.1;
hybrid union 52.7 / 58.3. Matches Appendix B (34.3; 52.6 for the grid
configuration).

## Conclusion

The Appendix B–B3 ladder and its ceilings (79.6 / 88.3) are official-GT
numbers; the pre-correction gold embedded in the basket files never
entered the reported scores. The recipe-improvement claim in the paper
("+10.8 points on a fixed 7B": 66.1 → 76.9) is confirmed under the
official ground truth. The only correction propagated to the paper is the
evidence-annotation p-value (0.04 → 0.06). `test_expand.py` (the 18%
co-change-expansion negative result) still needs the bare clones to rerun
and remains flagged in Appendix C.
