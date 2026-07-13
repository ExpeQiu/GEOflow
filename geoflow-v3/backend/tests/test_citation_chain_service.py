import pytest

from app.services.geoeval.citation_chain_service import _domain


def test_domain_extract():
    assert _domain("https://www.example.com/path") == "example.com"
    assert _domain("") == ""
