from app.services.geoeval.wiki_compliance import WikiGeoComplianceChecker


def test_wiki_compliance_pass():
    checker = WikiGeoComplianceChecker()
    content = "[link1](/a) [link2](/b) [link3](/c)\n| col | val |\n| --- | --- |"
    meta = {
        "quick_answer": "yes",
        "faq": [{"q": "a", "a": "b"}, {"q": "c", "a": "d"}],
        "last_updated": "2026-07-01",
    }
    result = checker.check(content, meta)
    assert result["passed"] is True


def test_wiki_compliance_fail():
    checker = WikiGeoComplianceChecker()
    result = checker.check("short", {})
    assert result["passed"] is False
    assert len(result["failures"]) > 0
