"""
Tests für github_client.py und subnet_github_mapper.py
"""

import json
import pytest
from pathlib import Path
import shutil
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from scorer.github_client import (
    CommitStats,
    RepoCoords,
    RepoStats,
    get_commits_last_30d,
    get_repo_from_url,
    get_repo_stats,
)
from scorer.subnet_github_mapper import get_github_coords


@pytest.fixture
def local_tmp_path():
    base = Path(__file__).resolve().parent.parent / "data" / "_test_tmp"
    path = base / f"github-mapper-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# get_repo_from_url
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected_owner,expected_repo", [
    ("https://github.com/opentensor/bittensor", "opentensor", "bittensor"),
    ("https://github.com/opentensor/bittensor.git", "opentensor", "bittensor"),
    ("https://github.com/opentensor/bittensor/tree/main", "opentensor", "bittensor"),
    ("github.com/owner/myrepo", "owner", "myrepo"),
    ("git@github.com:owner/repo.git", "owner", "repo"),
    ("https://github.com/owner/repo?tab=readme", "owner", "repo"),
    ("https://github.com/owner/repo/", "owner", "repo"),
])
def test_get_repo_from_url_valid(url, expected_owner, expected_repo):
    result = get_repo_from_url(url)
    assert result is not None
    assert result.owner == expected_owner
    assert result.repo == expected_repo


@pytest.mark.parametrize("url", [
    "",
    "https://gitlab.com/owner/repo",
    "not_a_url",
    "https://github.com/orgs/Beam-Network/repositories",
    None,
])
def test_get_repo_from_url_invalid(url):
    result = get_repo_from_url(url or "")
    assert result is None


# ---------------------------------------------------------------------------
# get_commits_last_30d
# ---------------------------------------------------------------------------

def _mock_commit(login="user1", email="user1@example.com"):
    return {
        "author": {"login": login},
        "commit": {"author": {"email": email}},
    }


def _make_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.headers = {"X-RateLimit-Remaining": "4999", **(headers or {})}
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_get_commits_last_30d_success():
    commits = [_mock_commit("alice"), _mock_commit("bob"), _mock_commit("alice")]
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[
        _make_response(200, commits),      # page 1
        _make_response(200, []),           # page 2 → empty, stop
    ])
    result = await get_commits_last_30d("owner", "repo", client=mock_client)
    assert isinstance(result, CommitStats)
    assert result.commits_30d == 3
    assert result.unique_contributors_30d == 2  # alice + bob


@pytest.mark.asyncio
async def test_get_commits_last_30d_not_found():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(404))
    result = await get_commits_last_30d("owner", "missing_repo", client=mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_get_commits_last_30d_empty_repo():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(409))
    result = await get_commits_last_30d("owner", "empty_repo", client=mock_client)
    assert result is not None
    assert result.commits_30d == 0
    assert result.unique_contributors_30d == 0


@pytest.mark.asyncio
async def test_get_commits_last_30d_http_error():
    import httpx
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_resp
    )
    mock_resp.headers = {"X-RateLimit-Remaining": "4999"}
    mock_client.get = AsyncMock(return_value=mock_resp)
    result = await get_commits_last_30d("owner", "repo", client=mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_get_commits_last_30d_handles_none_payload():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(200, None))
    result = await get_commits_last_30d("owner", "repo", client=mock_client)
    assert result is not None
    assert result.commits_30d == 0
    assert result.unique_contributors_30d == 0


@pytest.mark.asyncio
async def test_get_commits_last_30d_ignores_none_commit_entries():
    commits = [_mock_commit("alice"), None, _mock_commit("bob")]
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[
        _make_response(200, commits),
        _make_response(200, []),
    ])
    result = await get_commits_last_30d("owner", "repo", client=mock_client)
    assert result is not None
    assert result.commits_30d == 3
    assert result.unique_contributors_30d == 2


# ---------------------------------------------------------------------------
# get_repo_stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_repo_stats_success():
    data = {
        "stargazers_count": 1200,
        "forks_count": 300,
        "open_issues_count": 42,
        "pushed_at": "2025-01-20T10:00:00Z",
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(200, data))
    result = await get_repo_stats("owner", "repo", client=mock_client)
    assert isinstance(result, RepoStats)
    assert result.stars == 1200
    assert result.forks == 300
    assert result.open_issues == 42
    assert result.last_push == "2025-01-20T10:00:00Z"


@pytest.mark.asyncio
async def test_get_repo_stats_not_found():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(404))
    result = await get_repo_stats("owner", "missing", client=mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_get_repo_stats_private_repo():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(451))
    result = await get_repo_stats("owner", "private_repo", client=mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_get_repo_stats_handles_none_payload():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(200, None))
    result = await get_repo_stats("owner", "repo", client=mock_client)
    assert result is None


# ---------------------------------------------------------------------------
# subnet_github_mapper
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mapper_uses_override(local_tmp_path):
    overrides = {"1": {"owner": "override_owner", "repo": "override_repo"}}
    override_file = local_tmp_path / "github_map_overrides.json"
    override_file.write_text(json.dumps(overrides))

    with patch("scorer.subnet_github_mapper._OVERRIDES_PATH", override_file), \
         patch("scorer.subnet_github_mapper._MAP_PATH", local_tmp_path / "github_map.json"):
        result = await get_github_coords(1)

    assert result is not None
    assert result.owner == "override_owner"
    assert result.repo == "override_repo"


@pytest.mark.asyncio
async def test_mapper_uses_cache(local_tmp_path):
    cache = {"5": {"owner": "cached_owner", "repo": "cached_repo"}}
    cache_file = local_tmp_path / "github_map.json"
    cache_file.write_text(json.dumps(cache))

    with patch("scorer.subnet_github_mapper._OVERRIDES_PATH", local_tmp_path / "overrides.json"), \
         patch("scorer.subnet_github_mapper._MAP_PATH", cache_file):
        result = await get_github_coords(5)

    assert result is not None
    assert result.owner == "cached_owner"


@pytest.mark.asyncio
async def test_mapper_fetches_from_identity(local_tmp_path):
    from scorer.bittensor_client import SubnetIdentity

    identity = SubnetIdentity(
        netuid=10,
        name="mysubnet",
        github_url="https://github.com/myorg/myrepo",
    )

    with patch("scorer.subnet_github_mapper._OVERRIDES_PATH", local_tmp_path / "overrides.json"), \
         patch("scorer.subnet_github_mapper._MAP_PATH", local_tmp_path / "github_map.json"), \
         patch("scorer.subnet_github_mapper.get_subnet_identity", AsyncMock(return_value=identity)):
        result = await get_github_coords(10, live_fetch=True)

    assert result is not None
    assert result.owner == "myorg"
    assert result.repo == "myrepo"

    # Verify it was written to cache
    cache_data = json.loads((local_tmp_path / "github_map.json").read_text())
    assert cache_data["10"]["owner"] == "myorg"


@pytest.mark.asyncio
async def test_mapper_returns_none_when_no_github_url(local_tmp_path):
    from scorer.bittensor_client import SubnetIdentity

    identity = SubnetIdentity(netuid=99, name="nourl")

    with patch("scorer.subnet_github_mapper._OVERRIDES_PATH", local_tmp_path / "overrides.json"), \
         patch("scorer.subnet_github_mapper._MAP_PATH", local_tmp_path / "github_map.json"), \
         patch("scorer.subnet_github_mapper.get_subnet_identity", AsyncMock(return_value=identity)):
        result = await get_github_coords(99, live_fetch=True)

    assert result is None
