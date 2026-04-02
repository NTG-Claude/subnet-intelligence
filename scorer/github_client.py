"""
GitHub API Client
Async client for repository analysis via api.github.com
"""

import logging
import os
import re
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
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
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
                resp = await client.get(
                    url,
                    headers=_headers(),
                    params={**params, "page": page},
                    timeout=10.0,
                )
                _update_rate_limit(resp)

                if resp.status_code in (404, 451):  # not found or unavailable for legal reasons
                    logger.info("Repo %s/%s not accessible (status %s)", owner, repo, resp.status_code)
                    return None
                if resp.status_code == 409:  # empty repo
                    return CommitStats(owner=owner, repo=repo, commits_30d=0, unique_contributors_30d=0)

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

        authors = set()
        for c in commits:
            if not isinstance(c, dict):
                continue
            author = c.get("author") or {}
            commit = c.get("commit") or {}
            commit_author = commit.get("author") or {}
            authors.add(author.get("login") or commit_author.get("email"))
        authors.discard(None)

        return CommitStats(
            owner=owner,
            repo=repo,
            commits_30d=len(commits),
            unique_contributors_30d=len(authors),
        )

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
            resp = await client.get(url, headers=_headers(), timeout=10.0)
            _update_rate_limit(resp)

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
