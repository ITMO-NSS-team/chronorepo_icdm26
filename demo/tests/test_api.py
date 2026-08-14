"""API smoke tests. Uses a repository already cloned by test_parity.py
(or clones psf/requests once); no LLM calls are made."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app          # noqa: E402
from app.store import store       # noqa: E402

REPO = "psf/requests"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def index_id():
    return store.ensure(REPO).id


def test_config(client):
    cfg = client.get("/api/config").json()
    assert cfg["rrf_k"] == 40
    assert cfg["alpha"] == 0.25
    assert abs(cfg["lambda_per_day"] - 1 / 90) < 1e-12


def test_rejects_non_github_urls(client):
    for bad in ["file:///etc/passwd", "https://evil.example/x/y",
                "git@github.com:psf/requests.git", "../../etc", ""]:
        r = client.post("/api/index", json={"repo": bad})
        assert r.status_code == 400, bad


def test_repo_stats_and_graph(client, index_id):
    stats = client.get(f"/api/repos/{index_id}").json()
    assert stats["stats"]["py_files"] > 10
    assert stats["stats"]["cochange_pairs"] > 0
    assert stats["top_files"]

    g = client.get(f"/api/repos/{index_id}/graph?limit=40").json()
    assert len(g["nodes"]) <= 40
    assert g["temporal"] and all(e["ts"] for e in g["temporal"])
    assert g["lambda_per_day"] == pytest.approx(1 / 90)


def test_impact_methods(client, index_id):
    seed = client.get(f"/api/repos/{index_id}").json()["top_files"][0]["file"]
    d = client.get(f"/api/repos/{index_id}/impact?file={seed}&k=10").json()
    assert set(d["methods"]) == {"rose", "freq", "static_ppr", "temporal_ppr",
                                 "hybrid_a25"}
    for rows in d["methods"].values():
        assert all(r["file"] != seed for r in rows)


def test_localize_without_llm(client, index_id):
    issue = ("SSLError when a redirect changes scheme: Session.resolve_redirects "
             "drops the verify setting and requests.adapters.HTTPAdapter "
             "re-reads it from the environment.")
    d = client.post(f"/api/repos/{index_id}/localize",
                    json={"issue": issue, "depth": 25}).json()
    assert len(d["candidate_paths"]) > 10
    assert d["candidates"][0]["sources"], "provenance must be attached"
    assert "final" not in d
    assert d["timings_ms"]["fuse"] >= 0


def test_localize_rejects_empty_issue(client, index_id):
    r = client.post(f"/api/repos/{index_id}/localize", json={"issue": "hi"})
    assert r.status_code == 400


def test_unknown_index(client):
    assert client.get("/api/repos/nope@0000/graph").status_code == 404


def test_benchmarks_and_instances(client):
    b = client.get("/api/benchmarks").json()
    assert b["locbench_small"]["rows"]
    insts = client.get("/api/instances?repo=psf/requests").json()["instances"]
    assert insts and all(i["gold"] for i in insts)
    one = client.get(f"/api/instances/{insts[0]['id']}").json()
    assert one["issue"] and one["recorded"]["candidates"]


def test_static_route_does_not_escape_the_bundle(client):
    r = client.get("/../../../etc/passwd")
    assert r.status_code in (200, 404)
    assert "root:" not in r.text
    assert client.get("/api/definitely-not-a-route").status_code == 404
