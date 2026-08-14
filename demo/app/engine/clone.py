"""Repository acquisition: strict URL validation + bare clone/fetch.

Only https://github.com/<owner>/<repo> is accepted — this endpoint runs git
against user input, so no ssh, no file://, no arbitrary hosts.

Blobless clones (--filter=blob:none) were measured and rejected: git fetches
lazily one blob per round trip (49 s for 60 blobs of psf/requests), while a
full --no-tags --single-branch bare clone of the same repo takes 5.7 s. The
single branch is enough: everything downstream is filtered to the ancestor
set of the requested revision anyway.
"""
import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from ..config import settings

URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9._-]{0,38}))/"
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99}?))(?:\.git)?/?$")
SHORT_RE = re.compile(
    r"^(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9._-]{0,38}))/"
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99}))$")


class RepoError(Exception):
    pass


def parse_repo(url):
    """'https://github.com/psf/requests.git' | 'psf/requests' -> 'psf/requests'."""
    url = (url or "").strip()
    m = URL_RE.match(url) or SHORT_RE.match(url)
    if not m:
        raise RepoError("Expected a GitHub repository: "
                        "https://github.com/<owner>/<repo>")
    owner, name = m.group("owner"), m.group("name")
    if ".." in owner or ".." in name:
        raise RepoError("Invalid repository name")
    return f"{owner}/{name}"


def repo_dir_for(repo):
    return settings.repos_dir / (repo.replace("/", "__") + ".git")


def github_meta(repo, timeout=6):
    """Public repo metadata (size, description). Best effort."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "chronorepo-demo"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        return {"size_kb": d.get("size"), "description": d.get("description"),
                "stars": d.get("stargazers_count"),
                "default_branch": d.get("default_branch"),
                "pushed_at": d.get("pushed_at")}
    except Exception:
        return {}


_PROGRESS_RE = re.compile(r"(Receiving objects|Resolving deltas|"
                          r"Counting objects|Compressing objects):\s+(\d+)%")


def _run_git_streaming(args, cwd, progress, stage, timeout):
    """Run git, forwarding its --progress percentages to the callback."""
    p = subprocess.Popen(["git", *args], cwd=str(cwd) if cwd else None,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + timeout
    last = -1
    assert p.stderr is not None
    for raw in iter(p.stderr.readline, b""):
        if time.time() > deadline:
            p.kill()
            raise RepoError("git timed out")
        line = raw.decode("utf-8", "replace")
        m = _PROGRESS_RE.search(line)
        if m and progress:
            pct = int(m.group(2))
            if pct != last:
                last = pct
                progress(stage, "progress", phase=m.group(1), percent=pct)
    p.wait(timeout=max(1, deadline - time.time()))
    if p.returncode != 0:
        out = (p.stdout.read() if p.stdout else b"").decode("utf-8", "replace")
        raise RepoError(f"git {args[0]} failed: {out[:200]}")


def ensure_repo(repo, progress=None, rev=None):
    """Clone (or update) a bare mirror of `repo`; returns its path.

    Returns (path, meta) where meta carries what was done and how long it
    took — the UI shows real numbers, not an animation.
    """
    if settings.mode != "live":
        d = repo_dir_for(repo)
        if not d.exists():
            raise RepoError(f"{repo} is not available offline "
                            f"(mode={settings.mode})")
        return d, {"action": "cached", "ms": 0}

    d = repo_dir_for(repo)
    t0 = time.perf_counter()
    if d.exists():
        if progress:
            progress("clone", "start", action="fetch", repo=repo)
        _run_git_streaming(["-C", str(d), "fetch", "--no-tags", "--progress",
                            "origin", "+refs/heads/*:refs/heads/*"], None,
                           progress, "clone", settings.clone_timeout_s)
        action = "fetch"
    else:
        meta = github_meta(repo)
        size_mb = (meta.get("size_kb") or 0) / 1024
        if size_mb and size_mb > settings.max_repo_mb:
            raise RepoError(f"{repo} is {size_mb:.0f} MB, over the "
                            f"{settings.max_repo_mb} MB demo limit")
        if progress:
            progress("clone", "start", action="clone", repo=repo,
                     size_mb=round(size_mb) or None)
        tmp = d.with_suffix(".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            _run_git_streaming(
                ["clone", "--bare", "--no-tags", "--single-branch",
                 "--progress", f"https://github.com/{repo}.git", str(tmp)],
                None, progress, "clone", settings.clone_timeout_s)
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        tmp.rename(d)
        action = "clone"

    if rev and rev != "HEAD":
        # SWE-bench base commits can live on branches no ref points at;
        # GitHub serves arbitrary SHAs on a direct fetch.
        have = subprocess.run(
            ["git", "-C", str(d), "cat-file", "-e", rev + "^{commit}"],
            capture_output=True, check=False).returncode == 0
        if not have:
            subprocess.run(["git", "-C", str(d), "fetch", "origin", rev],
                           capture_output=True, check=False)

    ms = round((time.perf_counter() - t0) * 1000)
    _invalidate_history_cache(repo, d)
    if progress:
        progress("clone", "done", action=action, ms=ms,
                 mb=round(_dir_mb(d)))
    return d, {"action": action, "ms": ms, "mb": round(_dir_mb(d))}


def _dir_mb(path):
    total = 0
    for p in Path(path).rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total / 1e6


def _invalidate_history_cache(repo, repo_dir):
    """chrono.mine_history caches the full log; drop it when refs moved."""
    slug = repo.replace("/", "__")
    cache = settings.cache_dir / f"{slug}_log.pkl"
    stamp = settings.cache_dir / f"{slug}_log.head"
    heads = subprocess.run(["git", "-C", str(repo_dir), "rev-parse", "--all"],
                           capture_output=True, check=False).stdout
    digest = hashlib.sha1(heads).hexdigest()
    if stamp.exists() and stamp.read_text(encoding="utf-8") == digest:
        return
    cache.unlink(missing_ok=True)
    stamp.write_text(digest, encoding="utf-8")
