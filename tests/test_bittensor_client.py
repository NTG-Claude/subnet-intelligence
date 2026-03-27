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
    _fetch_current_block,
    _fetch_netuids,
    BLOCKS_PER_DAY,
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
    mock_st.get_all_subnet_netuids.return_value = [0, 1, 2, 3, 4]

    with patch("scorer.bittensor_client._subtensor", return_value=mock_st):
        result = _fetch_netuids()

    assert result == [0, 1, 2, 3, 4]


def test_fetch_netuids_handles_error():
    mock_st = MagicMock()
    mock_st.get_all_subnet_netuids.side_effect = RuntimeError("no connection")

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
