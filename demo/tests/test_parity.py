"""The demo must produce the paper's numbers, not its own.

These tests rebuild real SWE-bench Lite instances through the serving engine
and compare, element for element, against:
  * night_lab.rrf_final  — the recipe as the experiments call it;
  * data/rerank_final_lite.jsonl — the baskets the reported runs consumed;
  * chrono.temporal_edges — the graph layer the paper measures;
  * prepare_rerank50.evidence_str — the evidence strings shown to the model.

They need network on first run (bare clones land in demo/var/repos).
"""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.app.config import DATA                       # noqa: E402
from demo.app.engine import clone, serving             # noqa: E402
from demo.app.engine import evidence as ev             # noqa: E402

import chrono                                          # noqa: E402
import night_lab as nl                                 # noqa: E402
import prepare_rerank50 as pr50                        # noqa: E402

# small repos: the whole test suite clones a few tens of MB
INSTANCES = ["psf__requests-2317", "psf__requests-1963",
             "pallets__flask-4045", "mwaskom__seaborn-3010"]


def _load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture(scope="session")
def lite():
    return {r["instance_id"]: r for r in _load(DATA / "swebench_lite.jsonl")}


@pytest.fixture(scope="session")
def baskets():
    return {r["instance_id"]: r
            for r in _load(DATA / "rerank_final_lite.jsonl")}


@pytest.fixture(scope="session")
def built(lite):
    """{instance_id: (RepoIndex, instance)} — one index per instance."""
    out = {}
    for iid in INSTANCES:
        inst = lite[iid]
        repo_dir, _ = clone.ensure_repo(inst["repo"], rev=inst["base_commit"])
        idx = serving.build_index(inst["repo"], repo_dir,
                                  inst["base_commit"])
        out[iid] = (idx, inst)
    return out


@pytest.mark.parametrize("iid", INSTANCES)
def test_fuse_matches_rrf_final(built, iid):
    """_fuse() reproduces night_lab.rrf_final exactly (with provenance)."""
    idx, inst = built[iid]
    ctx, _ = idx.issue_ctx(inst["problem_statement"])
    expected = nl.rrf_final(ctx, k=serving.RRF_K, exclude=serving.EXCLUDE)

    rows = nl.mix(ctx, serving.ALPHA)
    ppr_bm = nl.hybrid(ctx, ctx["seed_bm"], rows, top=100)
    ppr_gr = nl.hybrid(ctx, ctx["seed_gr"], rows, top=100)
    got, score, sources = serving._fuse(ctx, ppr_bm, ppr_gr,
                                        k=serving.RRF_K,
                                        exclude=serving.EXCLUDE)
    assert got == expected
    # provenance must add up to the fused score
    for p in got[:20]:
        assert math.isclose(sum(s[2] for s in sources[p]), score[p],
                            rel_tol=1e-12)


@pytest.mark.parametrize("iid", INSTANCES)
def test_basket_matches_recorded_run(built, baskets, iid):
    """The live basket equals the one the reported rerank runs consumed."""
    idx, inst = built[iid]
    recorded = [c["file"] for c in baskets[iid]["hybrid_top"]]
    got = idx.localize(inst["problem_statement"], depth=10)["candidate_paths"]
    assert got == recorded


@pytest.mark.parametrize("iid", INSTANCES[:2])
def test_mine_pairs_equals_chrono_temporal_edges(built, iid):
    """The single-pass miner is chrono.temporal_edges (decayed and raw)."""
    idx, _ = built[iid]
    py_set = set(idx.py_files)
    dec = chrono.temporal_edges(idx.history, idx.ancestors, idx.base_ts,
                                serving.LAM, py_set)
    raw = chrono.temporal_edges(idx.history, idx.ancestors, idx.base_ts,
                                0.0, py_set)
    assert set(idx.pairs) == set(dec) == set(raw)
    for k, v in idx.pairs.items():
        assert v[0] == pytest.approx(raw[k])
        assert v[1] == pytest.approx(dec[k], rel=1e-12)


@pytest.mark.parametrize("iid", INSTANCES[:2])
def test_evidence_render_matches_experiments(built, iid):
    """UI chips render to the exact strings the LLM experiments used."""
    idx, inst = built[iid]
    ctx, _ = idx.issue_ctx(inst["problem_statement"])
    rows = nl.mix(ctx, serving.ALPHA)
    ppr = serving._ppr_scores(ctx, rows, idx.py_idx, idx.n_py)
    seed_top = [p for p, _ in ctx["seed_bm"][:serving.SEED_TOP]]
    ranked, _, _ = serving._fuse(ctx, nl.hybrid(ctx, ctx["seed_bm"], rows,
                                                top=100),
                                 nl.hybrid(ctx, ctx["seed_gr"], rows,
                                           top=100))
    for p in ranked[:25]:
        chips = ev.chips(seed_top, p, idx.s_edges, idx.t_raw,
                         ppr.get(p, 0.0), idx.last_seen)
        assert ev.render(chips) == pr50.evidence_str(
            seed_top, p, idx.s_edges, idx.t_raw, ppr.get(p, 0.0))


@pytest.mark.parametrize("iid", INSTANCES[:2])
def test_no_future_leakage(built, iid):
    """No commit outside the base commit's ancestor set enters the graph."""
    idx, inst = built[iid]
    assert inst["base_commit"] in idx.ancestors
    descendants = chrono.git(idx.repo_dir, "rev-list", "--all",
                             f"^{inst['base_commit']}").split()
    assert descendants, "expected the clone to contain later commits"
    assert not (set(descendants) & idx.ancestors)


@pytest.mark.parametrize("iid", INSTANCES[:1])
def test_timeline_stamps_reproduce_decayed_weight(built, iid):
    """The slider's client-side formula over per-edge commit stamps equals
    the server's decayed weight (this is what the timeline replays)."""
    idx, _ = built[iid]
    sub = idx.subgraph(limit=60)
    assert sub["temporal"], "expected co-change edges in the subgraph"
    for e in sub["temporal"][:25]:
        w = sum(math.exp(-serving.LAM * max(0.0, (idx.base_ts - t) / 86400.0))
                for t in e["ts"])
        assert w == pytest.approx(e["decayed"], abs=1e-3)
        assert len(e["ts"]) == e["count"]
