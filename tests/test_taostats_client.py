from unittest.mock import AsyncMock, patch

import pytest

from scorer.taostats_client import _extract_public_subnet_name, _extract_tao_app_subnet_name, _get


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


def test_extract_public_subnet_name_normalizes_mojibake_templar():
    html = (
        '<html><head><title>0.0448 Â· SN3 Â· Ï„emplar Â· taostats</title></head>'
        '<body>{"netuid":3,"name":"Ï„emplar"}</body></html>'
    )
    assert _extract_public_subnet_name(html, 3) == "Templar"


def test_extract_public_subnet_name_ignores_suspicious_meta_payload():
    html = (
        '<html><head><title>0.0044 · SN86 · taostats</title></head>'
        '<body>{"netuid":86,"name":"description","content":"0.0044 · SN86 · taostats\\"}],'
        '[\\"$\\",\\"meta\\",\\"1\\",{\\"name\\":\\"description\\"}]}'
        '</body></html>'
    )
    assert _extract_public_subnet_name(html, 86) is None


def test_extract_tao_app_subnet_name_from_heading():
    html = (
        "<html><body><h1>Subnet 20: GroundLayer</h1>"
        "<div>Price τ 0.003794|$1.24</div></body></html>"
    )
    assert _extract_tao_app_subnet_name(html, 20) == "GroundLayer"
