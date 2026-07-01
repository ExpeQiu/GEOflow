"""Wiki GEO 合规检查 — 移植 WikiGeoComplianceChecker。"""

import re


class WikiGeoComplianceChecker:
    def check(self, content: str, wiki_meta: dict) -> dict:
        failures: list[str] = []

        if not wiki_meta.get("quick_answer"):
            failures.append("missing_quick_answer")
        if content.count("|") < 2:
            failures.append("missing_table")
        if len(re.findall(r"\]\(/", content)) < 3:
            failures.append("insufficient_internal_links")
        faq = wiki_meta.get("faq") or []
        if len(faq) < 2:
            failures.append("insufficient_faq")
        if not wiki_meta.get("last_updated"):
            failures.append("missing_last_updated")

        return {"passed": len(failures) == 0, "failures": failures, "checks_run": 5}
