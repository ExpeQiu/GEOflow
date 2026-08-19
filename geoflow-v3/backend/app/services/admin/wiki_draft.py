"""Wiki 知识库生成草稿（Mock First，无 ORM）。"""

from __future__ import annotations

from typing import Any


def render_wiki_draft(
    *,
    title: str,
    wiki_page_type: str,
    hits: list[dict[str, Any]] | None,
    target_query: str = "",
    domain: str = "",
    mock: bool = True,
) -> dict[str, Any]:
    snippets: list[str] = []
    for hit in hits or []:
        text = str(hit.get("content") or "").strip()
        if text:
            snippets.append(text[:800])
        if len(snippets) >= 4:
            break

    query = (target_query or title).strip()
    if mock:
        quick = f"{title}：知识库草稿要点（Mock），发布前请人工改写。"
    elif snippets:
        quick = snippets[0].replace("\n", " ")[:120]
    else:
        quick = f"{title} 的 Wiki 草稿，待补全。"

    if not snippets:
        body = f"""## {title}

> 知识库暂无命中。以下为 Mock 骨架，请人工补全后发布。

### 要点
- 定义：{title} 是什么
- 适用场景与边界
- 与相邻技术的关系

### 参考问法
{query}
"""
    else:
        cited = "\n\n".join(f"### 语料 {i + 1}\n\n{s}" for i, s in enumerate(snippets))
        body = f"""## {title}

{quick}

{cited}

### 待编辑
请把语料改写成面向读者的 Wiki 正文，并补齐 related / FAQ 后再发布。
"""

    return {
        "body": body.strip() + "\n",
        "quick_answer": quick[:200],
        "core_takeaway": quick[:200],
        "target_query": query,
        "mock": mock,
        "hit_count": len(snippets),
        "wiki_page_type": wiki_page_type,
        "domain": domain or None,
    }
