from unittest.mock import AsyncMock, patch

import pytest

from scorer.taostats_client import _extract_public_subnet_name, _get


@pytest.mark.asyncio
async def test_get_skips_when_api_key_missing():
    client = AsyncMock()
    with patch("scorer.taostats_client._API_KEY", ""):
        result = await _get(client, "/subnet/latest/v1")

    assert result is None
    client.get.assert_not_called()


def test_extract_public_subnet_name_from_title():
    html = "<html><head><title>0.0448 Â· SN4 Â· Targon Â· taostats</title></head></html>"
    assert _extract_public_subnet_name(html, 4) == "Targon"


def test_extract_public_subnet_name_from_clean_middle_dot_title():
    html = "<html><head><title>0.0283 · SN9 · iota · taostats</title></head></html>"
    assert _extract_public_subnet_name(html, 9) == "iota"


def test_extract_public_subnet_name_from_body_when_title_missing():
    html = "<html><body><div>0.0283 · SN9 · iota · taostats</div></body></html>"
    assert _extract_public_subnet_name(html, 9) == "iota"


def test_extract_public_subnet_name_prefers_full_json_name_over_truncated_title():
    html = (
        '<html><head><title>0.0086 · SN13 · Data Uni... · taostats</title></head>'
        '<body>{"netuid":13,"name":"Data Universe","subnet_name":"Data Universe"}</body></html>'
    )
    assert _extract_public_subnet_name(html, 13) == "Data Universe"
