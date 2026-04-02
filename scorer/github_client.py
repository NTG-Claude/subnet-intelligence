"""
GitHub API Client
Async client for repository analysis via api.github.com
"""

import logging
import os
import re
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
_TOKEN = os.getenv("GITHUB_TOKEN", "")
_RATE_LIMIT_REMAINING = 5000  # updated from response headers
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class RepoCoords(BaseModel):
    owner: str
    repo: str


class CommitStats(BaseModel):
    owner: str
    repo: str
    commits_30d: int
    unique_contributors_30d: int
    last_commit_at: Optional[str] = None


class CommitActivitySummary(BaseModel):
    owner: str
    repo: str
    commits_30d: int
    unique_contributors_30d: int
    commits_90d: int
    unique_contributors_90d: int
    commits_180d: int
    unique_contributors_180d: int
    last_commit_at: Optional[str] = None


class RepoStats(BaseModel):
    owner: str
    repo: str
    stars: int
    forks: int
    open_issues: int
    last_push: Optional[str] = None  # ISO 8601


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    return h


def _update_rate_limit(response: httpx.Response) -> None:
    global _RATE_LIMIT_REMAINING
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        _RATE_LIMIT_REMAINING = int(remaining)
        if _RATE_LIMIT_REMAINING < 100:
            logger.warning("GitHub rate limit low: %s requests remaining", _RATE_LIMIT_REMAINING)


def _is_transient_http_status(status_code: int) -> bool:
    return status_code in _TRANSIENT_STATUS_CODES


async def _get_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[dict] = None,
    timeout: float = 10.0,
    attempts: int = 3,
) -> httpx.Response:
    last_exc: httpx.HTTPError | None = None
    for attempt in range(1, attempts + 1):
        try:
            resp = await client.get(url, headers=_headers(), params=params, timeout=timeout)
            _update_rate_limit(resp)
            if _is_transient_http_status(resp.status_code) and attempt < attempts:
                await asyncio.sleep(0.6 * attempt)
                continue
            return resp
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            await asyncio.sleep(0.6 * attempt)
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def get_repo_from_url(url: str) -> Optional[RepoCoords]:
    """
    Extract owner/repo from a GitHub URL.

    Handles formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/main
    - github.com/owner/repo
    - git@github.com:owner/repo.git
    """
    if not url:
        return None

    url = url.strip().rstrip("/")

    # SSH format: git@github.com:owner/repo.git
    ssh = re.match(r"git@github\.com:([^/]+)/([^/.]+)(?:\.git)?$", url)
    if ssh:
        return RepoCoords(owner=ssh.group(1), repo=ssh.group(2))

    # HTTPS / bare formats
    match = re.search(r"github\.com[/:]([^/]+)/([^/?#\s]+)", url)
    if not match:
        return None

    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")

    if not owner or not repo:
        return None

    # Organization listing URLs are not repositories.
    if owner.lower() == "orgs":
        return None

    return RepoCoords(owner=owner, repo=repo)


async def get_commits_last_30d(
    owner: str, repo: str, client: Optional[httpx.AsyncClient] = None
) -> Optional[CommitStats]:
    """
    Return commit count and unique contributor count for the last 30 days.
    Returns None if the repo is not found, private, or the request fails.
    """
    summary = await get_commit_activity_summary(owner, repo, client=client)
    if summary is None:
        return None
    return CommitStats(
        owner=owner,
        repo=repo,
        commits_30d=summary.commits_30d,
        unique_contributors_30d=summary.unique_contributors_30d,
        last_commit_at=summary.last_commit_at,
    )


def _coerce_commit_datetime(value: object) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _build_commit_activity_summary(owner: str, repo: str, commits: list[dict]) -> CommitActivitySummary:
    now = datetime.now(timezone.utc)
    windows = {
        30: now - timedelta(days=30),
        90: now - timedelta(days=90),
        180: now - timedelta(days=180),
    }
    counts = {30: 0, 90: 0, 180: 0}
    contributors = {30: set(), 90: set(), 180: set()}
    last_commit_at: Optional[datetime] = None

    for item in commits:
        if not isinstance(item, dict):
            continue
        commit = item.get("commit") or {}
        commit_author = commit.get("author") or {}
        timestamp = _coerce_commit_datetime(commit_author.get("date"))
        author = item.get("author") or {}
        contributor_id = author.get("login") or commit_author.get("email")

        if timestamp and (last_commit_at is None or timestamp > last_commit_at):
            last_commit_at = timestamp

        for days, cutoff in windows.items():
            if timestamp is None or timestamp < cutoff:
                continue
            counts[days] += 1
            if contributor_id:
                contributors[days].add(contributor_id)

    return CommitActivitySummary(
        owner=owner,
        repo=repo,
        commits_30d=counts[30],
        unique_contributors_30d=len(contributors[30]),
        commits_90d=counts[90],
        unique_contributors_90d=len(contributors[90]),
        commits_180d=counts[180],
        unique_contributors_180d=len(contributors[180]),
        last_commit_at=last_commit_at.isoformat() if last_commit_at else None,
    )


async def get_commit_activity_summary(
    owner: str, repo: str, client: Optional[httpx.AsyncClient] = None
) -> Optional[CommitActivitySummary]:
    """Return multi-horizon commit activity for the last 180 days."""
    since = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params = {"since": since, "per_page": 100}

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True)

    try:
        commits: list[dict] = []
        page = 1
        while True:
            try:
                resp = await _get_with_retries(
                    client,
                    url,
                    params={**params, "page": page},
                    timeout=10.0,
                )

                if resp.status_code in (404, 451):  # not found or unavailable for legal reasons
                    logger.info("Repo %s/%s not accessible (status %s)", owner, repo, resp.status_code)
                    return None
                if resp.status_code == 409:  # empty repo
                    return CommitActivitySummary(
                        owner=owner,
                        repo=repo,
                        commits_30d=0,
                        unique_contributors_30d=0,
                        commits_90d=0,
                        unique_contributors_90d=0,
                        commits_180d=0,
                        unique_contributors_180d=0,
                        last_commit_at=None,
                    )

                resp.raise_for_status()
                page_data = resp.json()
                if page_data is None:
                    page_data = []
                if not isinstance(page_data, list):
                    logger.warning(
                        "Unexpected commit payload for %s/%s: %s",
                        owner,
                        repo,
                        type(page_data).__name__,
                    )
                    return None

                if not page_data:
                    break

                commits.extend(page_data)

                # GitHub returns up to 100/page; stop if we got a full page to avoid abuse
                if len(page_data) < 100 or page >= 10:
                    break
                page += 1

            except httpx.HTTPStatusError as exc:
                logger.error("HTTP error fetching commits for %s/%s: %s", owner, repo, exc)
                return None
            except httpx.RequestError as exc:
                logger.error("Request error fetching commits for %s/%s: %s", owner, repo, exc)
                return None

        return _build_commit_activity_summary(owner, repo, commits)

    finally:
        if owns_client:
            await client.aclose()


async def get_repo_stats(
    owner: str, repo: str, client: Optional[httpx.AsyncClient] = None
) -> Optional[RepoStats]:
    """
    Return stars, forks, open issues, and last push date for a repo.
    Returns None if the repo is not accessible.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True)

    try:
        try:
            resp = await _get_with_retries(client, url, timeout=10.0)

            if resp.status_code in (404, 451):
                logger.info("Repo %s/%s not accessible (status %s)", owner, repo, resp.status_code)
                return None

            resp.raise_for_status()
            data = resp.json()
            if data is None:
                logger.warning("Empty repo payload for %s/%s", owner, repo)
                return None
            if not isinstance(data, dict):
                logger.warning(
                    "Unexpected repo payload for %s/%s: %s",
                    owner,
                    repo,
                    type(data).__name__,
                )
                return None

            return RepoStats(
                owner=owner,
                repo=repo,
                stars=data.get("stargazers_count", 0),
                forks=data.get("forks_count", 0),
                open_issues=data.get("open_issues_count", 0),
                last_push=data.get("pushed_at"),
            )

        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error fetching stats for %s/%s: %s", owner, repo, exc)
            return None
        except httpx.RequestError as exc:
            logger.error("Request error fetching stats for %s/%s: %s", owner, repo, exc)
            return None

    finally:
        if owns_client:
            await client.aclose()
