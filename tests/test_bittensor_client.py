"""
Unit tests for scorer/bittensor_client.py
Uses mocks — does not require a real chain connection.
"""

import pytest
from unittest.mock import MagicMock, patch

from scorer.bittensor_client import (
    SubnetIdentity,
    SubnetMetrics,
    _decode_bytes,
    _decode_identity_val,
    _fetch_current_block,
    _fetch_netuids,
    BLOCKS_PER_DAY,
    BLOCKS_PER_TEMPO,
)


# ---------------------------------------------------------------------------
# _decode_bytes
# ---------------------------------------------------------------------------

class TestDecodeBytes:
    def test_bytes(self):
        assert _decode_bytes(b"hello") == "hello"

    def test_list_of_ints(self):
        assert _decode_bytes([104, 101, 108, 108, 111]) == "hello"

    def test_str_passthrough(self):
        assert _decode_bytes("world") == "world"

    def test_none_returns_none(self):
        assert _decode_bytes(None) is None

    def test_empty_string_returns_none(self):
        assert _decode_bytes("") is None

    def test_null_bytes_stripped(self):
        assert _decode_bytes(b"hi\x00\x00") == "hi"


# ---------------------------------------------------------------------------
# _fetch_netuids (mocked subtensor)
# ---------------------------------------------------------------------------

def test_fetch_netuids_returns_list():
    mock_st = MagicMock()
    mock_st.get_all_subnets_netuid.return_value = [0, 1, 2, 3, 4]

    with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
        result = _fetch_netuids()

    assert result == [0, 1, 2, 3, 4]


def test_fetch_netuids_handles_error():
    mock_st = MagicMock()
    mock_st.get_all_subnets_netuid.side_effect = RuntimeError("no connection")

    with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
        result = _fetch_netuids()

    assert result == []


def test_fetch_current_block_returns_int():
    mock_st = MagicMock()
    mock_st.get_current_block.return_value = 4_500_000

    with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
        result = _fetch_current_block()

    assert result == 4_500_000


def test_fetch_current_block_handles_error():
    mock_st = MagicMock()
    mock_st.get_current_block.side_effect = ConnectionError("timeout")

    with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
        result = _fetch_current_block()

    assert result == 0


# ---------------------------------------------------------------------------
# SubnetMetrics dataclass
# ---------------------------------------------------------------------------

def test_subnet_metrics_defaults():
    m = SubnetMetrics(netuid=5)
    assert m.n_total == 0
    assert m.n_active_7d == 0
    assert m.total_stake_tao == 0.0
    assert m.unique_coldkeys == 0
    assert m.top3_stake_fraction == 1.0
    assert m.emission_per_block_tao == 0.0
    assert m.incentive_scores == []
    assert m.n_validators == 0
    assert m.registration_allowed is False
    assert m.immunity_period == 0


# ---------------------------------------------------------------------------
# SubnetIdentity dataclass
# ---------------------------------------------------------------------------

def test_subnet_identity_defaults():
    identity = SubnetIdentity(netuid=3)
    assert identity.name is None
    assert identity.github_url is None
    assert identity.website is None


# ---------------------------------------------------------------------------
# BLOCKS_PER_DAY sanity
# ---------------------------------------------------------------------------

def test_blocks_per_day_value():
    # ~12s per block → 7200 blocks/day
    assert BLOCKS_PER_DAY == 7200


def test_blocks_per_tempo_value():
    # one epoch = 360 blocks
    assert BLOCKS_PER_TEMPO == 360


# ---------------------------------------------------------------------------
# _decode_identity_val
# ---------------------------------------------------------------------------

class TestDecodeIdentityVal:
    def test_all_fields_bytes(self):
        val = {
            "subnet_name": b"Apex",
            "github_repo": b"opentensor/bittensor",
            "subnet_url": b"https://apex.io",
        }
        name, github, website = _decode_identity_val(val)
        assert name == "Apex"
        assert github == "opentensor/bittensor"
        assert website == "https://apex.io"

    def test_v1_field_names(self):
        val = {"name": "MySubnet", "github_url": "https://github.com/x/y", "url": "https://x.io"}
        name, github, website = _decode_identity_val(val)
        assert name == "MySubnet"
        assert github == "https://github.com/x/y"
        assert website == "https://x.io"

    def test_missing_fields_return_none(self):
        name, github, website = _decode_identity_val({})
        assert name is None
        assert github is None
        assert website is None

    def test_prefers_v2_subnet_name_over_name(self):
        val = {"subnet_name": b"V2Name", "name": "V1Name"}
        name, _, _ = _decode_identity_val(val)
        assert name == "V2Name"


# ---------------------------------------------------------------------------
# _fetch_all_identities_sync (mocked)
# ---------------------------------------------------------------------------

def test_fetch_all_identities_sync_populates_cache():
    import scorer.bittensor_client as bt_client
    from scorer.bittensor_client import _fetch_all_identities_sync

    # Reset module state
    original_fetched = bt_client._all_identities_fetched
    original_cache = bt_client._identity_cache.copy()
    bt_client._all_identities_fetched = False
    bt_client._identity_cache.clear()

    mock_entry_key = MagicMock()
    mock_entry_key.value = 4
    mock_entry_val = MagicMock()
    mock_entry_val.value = {"subnet_name": b"Targon", "github_repo": None, "subnet_url": None}

    mock_st = MagicMock()
    mock_st.substrate.query_map.return_value = [(mock_entry_key, mock_entry_val)]

    try:
        with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
            _fetch_all_identities_sync()

        assert bt_client._all_identities_fetched is True
        assert 4 in bt_client._identity_cache
        assert bt_client._identity_cache[4].name == "Targon"
    finally:
        # Restore state
        bt_client._all_identities_fetched = original_fetched
        bt_client._identity_cache.clear()
        bt_client._identity_cache.update(original_cache)


def test_fetch_all_identities_sync_handles_query_map_failure():
    import scorer.bittensor_client as bt_client
    from scorer.bittensor_client import _fetch_all_identities_sync

    bt_client._all_identities_fetched = False

    mock_st = MagicMock()
    mock_st.substrate.query_map.side_effect = RuntimeError("storage not found")

    try:
        with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
            _fetch_all_identities_sync()  # should not raise
        assert bt_client._all_identities_fetched is True
    finally:
        bt_client._all_identities_fetched = False


def test_clear_caches_resets_identity_state():
    import scorer.bittensor_client as bt_client

    bt_client._identity_cache[1] = SubnetIdentity(netuid=1, name="x")
    bt_client._all_identities_fetched = True
    bt_client.clear_caches()

    assert bt_client._identity_cache == {}
    assert bt_client._all_identities_fetched is False
