"""
Mock-Tests für TaostatsClient — alle 8 Endpoints
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from scorer.taostats_client import (
    TaostatsClient,
    SubnetInfo,
    SubnetHistoryPoint,
    NeuronInfo,
    NeuronRegistration,
    ColdkeyDistribution,
    SubnetPool,
    SubnetIdentity,
    ValidatorWeight,
    _cache,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SUBNET_RECORD = {
    "netuid": 1,
    "name": "apex",
    "emission_percent": 2.5,
    "market_cap_usd": 1_000_000.0,
    "price_usd": 0.05,
    "flow_24h": 5_000.0,
    "flow_7d": 30_000.0,
    "flow_30d": 120_000.0,
    "liquidity_usd": 500_000.0,
    "volume_24h": 20_000.0,
}

HISTORY_RECORD = {
    "netuid": 1,
    "timestamp": "2025-01-01T00:00:00Z",
    "price_usd": 0.04,
    "market_cap_usd": 900_000.0,
    "emission_percent": 2.3,
}

NEURON_RECORD = {
    "uid": 0,
    "hotkey": "5ABC",
    "stake": 1000.0,
    "emission": 0.5,
    "incentive": 0.8,
    "trust": 0.9,
    "rank": 0.7,
    "active": True,
}

REGISTRATION_RECORD = {
    "netuid": 1,
    "hotkey": "5DEF",
    "registered_at": "2025-01-15T12:00:00Z",
}

COLDKEY_RECORD = {
    "netuid": 1,
    "unique_coldkeys": 250,
    "top3_stake_percent": 0.12,
    "gini_coefficient": 0.45,
}

POOL_RECORD = {
    "netuid": 1,
    "liquidity_usd": 500_000.0,
    "volume_24h": 20_000.0,
    "price": 0.05,
}

IDENTITY_RECORD = {
    "netuid": 1,
    "name": "apex",
    "github_url": "https://github.com/opentensor/bittensor",
    "website": "https://bittensor.com",
    "description": "The root subnet",
}

WEIGHT_RECORD = {
    "netuid": 1,
    "hotkey": "5GHI",
    "weight_commits": 42,
    "last_updated": "2025-01-20T08:00:00Z",
}


def _mock_response(payload) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture(autouse=True)
def clear_cache():
    _cache.clear()
    yield
    _cache.clear()


# ---------------------------------------------------------------------------
# Helper to patch _get
# ---------------------------------------------------------------------------

def _patch_get(return_value):
    return patch("scorer.taostats_client._get", new=AsyncMock(return_value=return_value))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_subnets_returns_list():
    with _patch_get([SUBNET_RECORD, SUBNET_RECORD]):
        async with TaostatsClient() as client:
            result = await client.get_all_subnets()
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], SubnetInfo)
    assert result[0].netuid == 1
    assert result[0].name == "apex"


@pytest.mark.asyncio
async def test_get_all_subnets_wrapped_in_data_key():
    with _patch_get({"data": [SUBNET_RECORD]}):
        async with TaostatsClient() as client:
            result = await client.get_all_subnets()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_all_subnets_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_all_subnets()
    assert result is None


@pytest.mark.asyncio
async def test_get_subnet_history():
    with _patch_get([HISTORY_RECORD]):
        async with TaostatsClient() as client:
            result = await client.get_subnet_history(netuid=1, days=30)
    assert isinstance(result, list)
    assert isinstance(result[0], SubnetHistoryPoint)
    assert result[0].netuid == 1


@pytest.mark.asyncio
async def test_get_subnet_history_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_subnet_history(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_metagraph():
    with _patch_get([NEURON_RECORD]):
        async with TaostatsClient() as client:
            result = await client.get_metagraph(netuid=1)
    assert isinstance(result, list)
    assert isinstance(result[0], NeuronInfo)
    assert result[0].uid == 0
    assert result[0].active is True


@pytest.mark.asyncio
async def test_get_metagraph_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_metagraph(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_neuron_registrations():
    with _patch_get([REGISTRATION_RECORD]):
        async with TaostatsClient() as client:
            result = await client.get_neuron_registrations(netuid=1, days=7)
    assert isinstance(result, list)
    assert isinstance(result[0], NeuronRegistration)
    assert result[0].hotkey == "5DEF"


@pytest.mark.asyncio
async def test_get_neuron_registrations_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_neuron_registrations(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_coldkey_distribution():
    with _patch_get(COLDKEY_RECORD):
        async with TaostatsClient() as client:
            result = await client.get_coldkey_distribution(netuid=1)
    assert isinstance(result, ColdkeyDistribution)
    assert result.unique_coldkeys == 250


@pytest.mark.asyncio
async def test_get_coldkey_distribution_list_response():
    with _patch_get([COLDKEY_RECORD]):
        async with TaostatsClient() as client:
            result = await client.get_coldkey_distribution(netuid=1)
    assert isinstance(result, ColdkeyDistribution)


@pytest.mark.asyncio
async def test_get_coldkey_distribution_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_coldkey_distribution(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_subnet_pools():
    with _patch_get(POOL_RECORD):
        async with TaostatsClient() as client:
            result = await client.get_subnet_pools(netuid=1)
    assert isinstance(result, SubnetPool)
    assert result.liquidity_usd == 500_000.0


@pytest.mark.asyncio
async def test_get_subnet_pools_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_subnet_pools(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_subnet_identity():
    with _patch_get(IDENTITY_RECORD):
        async with TaostatsClient() as client:
            result = await client.get_subnet_identity(netuid=1)
    assert isinstance(result, SubnetIdentity)
    assert result.github_url == "https://github.com/opentensor/bittensor"


@pytest.mark.asyncio
async def test_get_subnet_identity_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_subnet_identity(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_validator_weights():
    with _patch_get([WEIGHT_RECORD]):
        async with TaostatsClient() as client:
            result = await client.get_validator_weights(netuid=1)
    assert isinstance(result, list)
    assert isinstance(result[0], ValidatorWeight)
    assert result[0].weight_commits == 42


@pytest.mark.asyncio
async def test_get_validator_weights_returns_none_on_api_error():
    with _patch_get(None):
        async with TaostatsClient() as client:
            result = await client.get_validator_weights(1)
    assert result is None


@pytest.mark.asyncio
async def test_malformed_record_is_skipped():
    # Second record has no netuid → pydantic will try to parse; we just want no crash
    with _patch_get([{"netuid": 1}, {"completely_wrong_key": True}]):
        async with TaostatsClient() as client:
            result = await client.get_all_subnets()
    assert result is not None
