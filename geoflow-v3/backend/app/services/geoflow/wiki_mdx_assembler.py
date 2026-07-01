"""Wiki MDX 组装。"""

from app.models.article import Article


class WikiMdxAssembler:
    @staticmethod
    def assemble(article: Article) -> str:
        meta = article.wiki_meta or {}
        fm_lines = [f"{k}: {v}" for k, v in meta.items()]
        frontmatter = "\n".join(fm_lines)
        return f"---\n{frontmatter}\n---\n\n{article.content}"
