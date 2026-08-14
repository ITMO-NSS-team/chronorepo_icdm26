"""Paths, settings and the sys.path bootstrap for the experiment library.

Importing this module makes `chrono` and `night_lab` (which live in
experiments/ and are the code the paper's numbers come from) importable, so
the demo never carries a second copy of the method.
"""
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "experiments"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
DEMO = ROOT / "demo"

if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))


def load_dotenv(path=ROOT / ".env"):
    """Minimal .env reader (no dependency); does not override real env."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip("'\""))


load_dotenv()


def _env_bool(name, default):
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes")


def _env_int(name, default):
    v = os.environ.get(name)
    return int(v) if v else default


@dataclass
class Settings:
    # modes ------------------------------------------------------------
    mode: str = os.environ.get("CHRONO_MODE", "live")  # live|snapshot|booth
    allow_llm: bool = _env_bool("CHRONO_ALLOW_LLM", True)

    # storage ----------------------------------------------------------
    repos_dir: Path = DEMO / "var" / "repos"
    cache_dir: Path = DEMO / "var" / "cache"        # mine_history pickles
    snapshots_dir: Path = DEMO / "snapshots"
    web_dist: Path = DEMO / "web" / "dist"

    # limits -----------------------------------------------------------
    max_indexes_in_memory: int = _env_int("CHRONO_MAX_INDEXES", 3)
    max_concurrent_index_jobs: int = 2
    clone_timeout_s: int = _env_int("CHRONO_CLONE_TIMEOUT", 900)
    max_repo_mb: int = _env_int("CHRONO_MAX_REPO_MB", 4096)
    index_rate_per_min: int = _env_int("CHRONO_INDEX_RATE", 6)
    llm_rate_per_min: int = _env_int("CHRONO_LLM_RATE", 20)

    # llm --------------------------------------------------------------
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    models: tuple = (
        # (id, label, note) — the lanes reported in the paper
        ("qwen/qwen3.5-9b", "Qwen3.5-9B", "small-model lane · 80.5 Acc@5"),
        ("qwen/qwen-2.5-7b-instruct", "Qwen2.5-7B", "paper baseline · 76.9"),
        ("qwen/qwen3-coder", "Qwen3-Coder", "MoE · 81.0"),
        ("moonshotai/kimi-k2-0905", "Kimi-K2", "MoE · 83.7 at depth 100"),
    )
    default_model: str = os.environ.get("CHRONO_MODEL", "qwen/qwen3.5-9b")
    llm_timeout_s: int = 120

    # demo content -----------------------------------------------------
    bundled_repos: tuple = (
        "pallets/flask", "psf/requests", "mwaskom/seaborn",
        "sphinx-doc/sphinx", "django/django",
    )
    cors_origins: tuple = field(default_factory=lambda: tuple(
        o for o in os.environ.get(
            "CHRONO_CORS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if o))

    def openrouter_key(self):
        k = os.environ.get("OPENROUTER_API_KEY")
        if not k:
            f = EXPERIMENTS / ".openrouter_key"
            if f.exists():
                k = f.read_text(encoding="utf-8").strip()
        return k or None

    def ensure_dirs(self):
        for d in (self.repos_dir, self.cache_dir, self.snapshots_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
