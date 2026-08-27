# 构建日志 2026-08-26：Techstore → GEOFlow 知识库打通

- 范围：ADR-014。只读导入，按域拆 KB + 技术 IP upsert。
- 入口：`POST /api/admin/knowledge-bases/import-techstore`、知识库页按钮、`scripts/import_techstore_knowledge.py`
- 验收：`pytest tests/test_techstore_knowledge_import.py`；fixture 不含草稿；`g-ads` 进 tech-assets。
