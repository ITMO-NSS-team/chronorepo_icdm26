"""Human-readable evidence for a ranked file.

Structured version of `prepare_rerank50.evidence_str`; `render()` reproduces
that function's string exactly (asserted in tests/test_parity.py), so the UI
chips and the LLM annotations of the experiments stay one artifact.
"""
from datetime import datetime, timezone


def base(path):
    return path.rsplit("/", 1)[-1]


def month(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%b %Y")


def chips(seed_top, target, s_edges, t_raw, ppr_score, last_seen=None):
    """Evidence chips for `target` given the seed files it was pulled by.

    seed_top  : ordered seed paths (top-10 BM25 in the experiments)
    s_edges   : {(a,b): 1.0} import edges
    t_raw     : {(a,b): count} undecayed co-change counts
    last_seen : optional {(a,b): unix ts} of the last shared commit
    """
    out = []
    best = None
    for p in seed_top:
        e = t_raw.get(tuple(sorted((p, target))))
        if e and (best is None or e > best[1]):
            best = (p, e)
    if best:
        ts = (last_seen or {}).get(tuple(sorted((best[0], target))))
        out.append({"kind": "cochange", "with": best[0],
                    "count": int(best[1]), "last": month(ts)})
    for p in seed_top:
        if tuple(sorted((p, target))) in s_edges:
            out.append({"kind": "import", "with": p})
            break
    if ppr_score > 0:
        out.append({"kind": "graph", "score": round(ppr_score, 4)})
    return out[:3]


def render(chip_list):
    """Same string as prepare_rerank50.evidence_str."""
    parts = []
    for c in chip_list:
        if c["kind"] == "cochange":
            parts.append(f"co-changed with {base(c['with'])} x{c['count']}")
        elif c["kind"] == "import":
            parts.append(f"import link to {base(c['with'])}")
        elif c["kind"] == "graph":
            parts.append(f"graph score {c['score']:.2f}")
    return "; ".join(parts[:3])


def bridge(a, b, adj, exclude=(), top=1):
    """Two-hop bridges between a and b over a co-change adjacency."""
    na, nb = adj.get(a, {}), adj.get(b, {})
    if not na or not nb:
        return []
    common = (set(na) & set(nb)) - {a, b} - set(exclude)
    scored = sorted(common, key=lambda m: -min(na[m], nb[m]))[:top]
    return [{"kind": "bridge", "via": m,
             "count": int(min(na[m], nb[m]))} for m in scored]
