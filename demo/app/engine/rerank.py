"""The one LLM call: same prompt as the experiments, real cost accounting.

The system prompt and the user-message layout are imported from
experiments/run_rerank.py (condition `hybrid_plain`, paths only), so the demo
cannot silently drift from the runs the paper reports. Token usage comes back
from OpenRouter and is multiplied by that model's live per-token price, so
the cost meter shows what the call actually cost.
"""
import json
import re
import threading
import time
import urllib.error
import urllib.request

from ..config import settings

import run_rerank as rr

SYSTEM = rr.PROMPTS["default"]
ISSUE_CHARS = 1500          # prepare_final.py truncates the issue the same way
MAX_LIST = rr.MAX_LIST      # the model is asked for up to 10 paths


class LLMError(Exception):
    pass


def build_prompt(issue, candidate_paths):
    """run_rerank.build_prompt, condition 'hybrid_plain' (paths only)."""
    rec = {"issue": issue[:ISSUE_CHARS],
           "hybrid_top": [{"file": p} for p in candidate_paths]}
    prompt, cands = rr.build_prompt(rec, "hybrid_plain")
    return prompt, cands


def parse_ranked(text, candidate_paths):
    """run_rerank.parse_ranking (falls back to candidate order)."""
    return rr.parse_ranking(text or "", candidate_paths)


# ------------------------------------------------------------------ pricing

_PRICES = {}
_PRICES_AT = 0.0
_PRICE_LOCK = threading.Lock()


def prices(refresh=False):
    """{model_id: (prompt_usd_per_token, completion_usd_per_token)}."""
    global _PRICES_AT
    with _PRICE_LOCK:
        if _PRICES and not refresh and time.time() - _PRICES_AT < 3600:
            return _PRICES
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/models",
                headers={"User-Agent": "chronorepo-demo"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.load(r)
            for m in data.get("data", []):
                p = m.get("pricing") or {}
                try:
                    _PRICES[m["id"]] = (float(p.get("prompt", 0)),
                                        float(p.get("completion", 0)))
                except (TypeError, ValueError):
                    continue
            _PRICES_AT = time.time()
        except Exception:
            pass
        return _PRICES


def cost_of(model, prompt_tokens, completion_tokens):
    pp, pc = prices().get(model, (None, None))
    if pp is None:
        return None
    return round(pp * prompt_tokens + pc * completion_tokens, 8)


# ------------------------------------------------------------------ call

def call(issue, candidate_paths, model=None, temperature=0.0, timeout=None):
    key = settings.openrouter_key()
    if not key:
        raise LLMError("No OPENROUTER_API_KEY (put it in .env)")
    model = model or settings.default_model
    prompt, candidate_paths = build_prompt(issue, candidate_paths)
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 1500,   # thinking models spend budget before answering
    }).encode()
    req = urllib.request.Request(
        settings.openrouter_url, data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/chronorepo/demo",
                 "X-Title": "ChronoRepo demo"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(
                req, timeout=timeout or settings.llm_timeout_s) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise LLMError(f"OpenRouter {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise LLMError(f"OpenRouter unreachable: {e.reason}") from None
    ms = round((time.perf_counter() - t0) * 1000)

    if "error" in data and not data.get("choices"):
        raise LLMError(str(data["error"])[:200])
    msg = data["choices"][0]["message"]
    # thinking models may put the answer only in `reasoning`
    text = (msg.get("content") or msg.get("reasoning") or "").strip()
    ranked = parse_ranked(text, candidate_paths)
    usage = data.get("usage") or {}
    pt = usage.get("prompt_tokens", 0)
    ct = usage.get("completion_tokens", 0)
    return {
        "model": data.get("model", model),
        "ranked": ranked,
        "raw": text[:2000],
        "ms": ms,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "usd": cost_of(data.get("model", model), pt, ct),
        "n_candidates": len(candidate_paths),
    }
