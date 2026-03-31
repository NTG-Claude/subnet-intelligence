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
    html = "<html><head><title>0.0448 · SN4 · Targon · taostats</title></head></html>"
    assert _extract_public_subnet_name(html, 4) == "Targon"
