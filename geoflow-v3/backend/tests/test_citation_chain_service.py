from app.services.geoeval.citation_chain_service import _domain, stamp_citation_owners
from app.services.geoeval.domain_catalog import OWNER_OURS, OWNER_THIRD


def test_domain_extract():
    assert _domain("https://www.example.com/path") == "example.com"
    assert _domain("") == ""


def test_stamp_citation_owners():
    items = [
        {"url": "https://127.0.0.1:3070/concepts/x", "domain": "127.0.0.1"},
        {"url": "https://www.autohome.com.cn/x", "domain": "autohome.com.cn"},
    ]
    stamp_citation_owners(items, official=["127.0.0.1"], wiki=["wikipedia.org"])
    assert items[0]["owner"] == OWNER_OURS
    assert items[1]["owner"] == OWNER_THIRD
