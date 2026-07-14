"""ragc CLI — 知识库作业型命令。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from ragc import __version__
from ragc.config import load_settings
from ragc.core.chunking import split_with_overlap
from ragc.core.ingest import read_ingest_file
from ragc.core.retrieve import retrieve
from ragc.core.store import LocalStore
from ragc.core.sync import sync_knowledge_base
from ragc.utils.errors import EXIT_ERROR, EXIT_OK, EXIT_USAGE, StoreError, UsageError
from ragc.utils.logger import get_logger, setup_logging

logger = get_logger("ragc.cli")

DEMO_DOC = """# GEO 与 RAG 演示文档

生成式引擎优化（GEO）关注品牌在 AI 回答中的可见性。
知识库检索（RAG）通过切分、向量化与混合召回，为内容生产提供证据。

第二段：Embedding 将文本映射为向量，相似语义可在向量空间靠近。
第三段：生产化同步应支持全量重建、可复现 mock、以及离线验收。
"""


def _emit(data: Any, *, fmt: str, output: str | None) -> None:
    if fmt == "json":
        text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = _format_table(data)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
        click.echo(f"已写入 {output}", err=True)
    else:
        click.echo(text)


def _format_table(data: Any) -> str:
    if isinstance(data, dict) and data.get("module") == "kb-list":
        lines = [f"{'ID':<6} {'NAME':<24} CHARS  CHUNKS", "-" * 56]
        for item in data.get("items") or []:
            lines.append(
                f"{item.get('id', ''):<6} {str(item.get('name', ''))[:24]:<24} "
                f"{item.get('content_chars', 0):<6} {item.get('chunk_count', 0)}"
            )
        return "\n".join(lines)
    if isinstance(data, dict) and "hits" in data:
        lines = [
            f"kb={data.get('knowledge_base_id')} name={data.get('knowledge_base_name')}",
            f"query={data.get('query')} hits={data.get('hit_count')}",
            "-" * 56,
        ]
        for h in data.get("hits") or []:
            preview = str(h.get("content") or "")[:80].replace("\n", " ")
            lines.append(f"[{h.get('source')}|{h.get('score')}] #{h.get('chunk_index')} {preview}")
        return "\n".join(lines)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _envelope(module: str, payload: dict[str, Any], *, data_source: str) -> dict[str, Any]:
    return {
        "module": module,
        "version": __version__,
        "data_source": data_source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }


def _open_store(ctx: click.Context) -> LocalStore:
    settings = ctx.obj["settings"]
    store = LocalStore(settings.store_path)
    store.load()
    return store


@click.group()
@click.version_option(__version__, prog_name="ragc")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-q", "--quiet", is_flag=True)
@click.option("--store", "store_path", default=None, help="本地 store.json 路径")
@click.option("--config", "config_file", default=None, help="config.yaml 路径")
@click.option("--mock/--no-mock", default=None, help="Mock embedding（默认开）")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    store_path: str | None,
    config_file: str | None,
    mock: bool | None,
) -> None:
    """RAG-CLI — 切分 / Embedding / Sync / Query（独立于 GEOFlow）。"""
    setup_logging(verbose=verbose, quiet=quiet)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = load_settings(store_path=store_path, config_file=config_file, mock=mock)


@cli.group()
def kb() -> None:
    """知识库 CRUD。"""


@kb.command("list")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.option("-o", "--output", "output_path", default=None)
@click.pass_context
def kb_list(ctx: click.Context, fmt: str, output_path: str | None) -> None:
    store = _open_store(ctx)
    items = store.list_kbs()
    _emit(
        _envelope("kb-list", {"count": len(items), "items": items}, data_source="store"),
        fmt=fmt,
        output=output_path,
    )


@kb.command("create")
@click.option("--name", required=True)
@click.option("--content", default="")
@click.option("--file", "content_file", default=None)
@click.option("--demo", is_flag=True, help="使用内置演示文档")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.pass_context
def kb_create(
    ctx: click.Context,
    name: str,
    content: str,
    content_file: str | None,
    demo: bool,
    fmt: str,
) -> None:
    try:
        if demo:
            content = DEMO_DOC
            name = name or "demo-kb"
        elif content_file:
            _, content = read_ingest_file(content_file)
        store = _open_store(ctx)
        kb_row = store.create_kb(name, content)
        _emit(
            _envelope(
                "kb-create",
                {
                    "id": kb_row["id"],
                    "name": kb_row["name"],
                    "content_chars": len(kb_row.get("content") or ""),
                },
                data_source="demo" if demo else "store",
            ),
            fmt=fmt,
            output=None,
        )
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc


@kb.command("show")
@click.argument("kb_id", type=int)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.pass_context
def kb_show(ctx: click.Context, kb_id: int, fmt: str) -> None:
    try:
        store = _open_store(ctx)
        kb_row = store.get_kb(kb_id)
        _emit(
            _envelope(
                "kb-show",
                {
                    "id": kb_row["id"],
                    "name": kb_row["name"],
                    "content_chars": len(kb_row.get("content") or ""),
                    "chunk_count": len(kb_row.get("chunks") or []),
                    "synced_at": kb_row.get("synced_at"),
                    "content_preview": str(kb_row.get("content") or "")[:240],
                },
                data_source="store",
            ),
            fmt=fmt,
            output=None,
        )
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc


@kb.command("delete")
@click.argument("kb_id", type=int)
@click.pass_context
def kb_delete(ctx: click.Context, kb_id: int) -> None:
    try:
        store = _open_store(ctx)
        store.delete_kb(kb_id)
        _emit(_envelope("kb-delete", {"id": kb_id, "ok": True}, data_source="store"), fmt="json", output=None)
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc


@cli.command("ingest")
@click.argument("kb_id", type=int)
@click.option("--file", "file_path", required=True)
@click.option("--sync", "do_sync", is_flag=True, help="ingest 后立即 sync")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.pass_context
def ingest_cmd(ctx: click.Context, kb_id: int, file_path: str, do_sync: bool, fmt: str) -> None:
    """追加文件正文到知识库。"""
    try:
        filename, text = read_ingest_file(file_path)
        store = _open_store(ctx)
        store.update_content(kb_id, text, append=True, note=f"文件导入: {filename}")
        result: dict[str, Any] = {
            "knowledge_base_id": kb_id,
            "filename": filename,
            "character_count": len(text),
        }
        if do_sync:
            result["sync"] = sync_knowledge_base(store, kb_id, ctx.obj["settings"])
        _emit(_envelope("ingest", result, data_source="store"), fmt=fmt, output=None)
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc


@cli.command("sync")
@click.argument("kb_id", type=int, required=False)
@click.option("--demo", is_flag=True, help="创建演示 KB 并 sync（离线验收）")
@click.option("--chunk-size", type=int, default=None)
@click.option("--chunk-overlap", type=int, default=None)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.pass_context
def sync_cmd(
    ctx: click.Context,
    kb_id: int | None,
    demo: bool,
    chunk_size: int | None,
    chunk_overlap: int | None,
    fmt: str,
) -> None:
    """全量切分 + Embedding + 重建 chunks（生产主作业）。"""
    try:
        settings = load_settings(
            store_path=ctx.obj["settings"].store_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            mock=ctx.obj["settings"].mock_mode,
        )
        ctx.obj["settings"] = settings
        store = LocalStore(settings.store_path)
        store.load()
        data_source = "store"
        if demo:
            kb_row = store.create_kb("demo-kb", DEMO_DOC)
            kb_id = int(kb_row["id"])
            data_source = "demo"
        if kb_id is None:
            raise UsageError("请提供 kb_id，或使用 --demo")
        result = sync_knowledge_base(store, kb_id, settings)
        _emit(_envelope("sync", result, data_source=data_source), fmt=fmt, output=None)
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc
    except StoreError as exc:
        click.echo(f"存储错误: {exc}", err=True)
        raise SystemExit(EXIT_ERROR) from exc


@cli.command("query")
@click.argument("kb_id", type=int)
@click.argument("query_text")
@click.option("--limit", type=int, default=None)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("-o", "--output", "output_path", default=None)
@click.pass_context
def query_cmd(
    ctx: click.Context,
    kb_id: int,
    query_text: str,
    limit: int | None,
    fmt: str,
    output_path: str | None,
) -> None:
    """RAG 检索（等同 GEOFlow rag-sandbox）。"""
    try:
        if not query_text.strip():
            raise UsageError("query 不能为空")
        store = _open_store(ctx)
        result = retrieve(store, kb_id, query_text[:500], ctx.obj["settings"], limit=limit)
        _emit(_envelope("query", result, data_source="store"), fmt=fmt, output=output_path)
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc


@cli.command("chunk")
@click.option("--file", "file_path", default=None)
@click.option("--text", default=None)
@click.option("--demo", is_flag=True)
@click.option("--chunk-size", type=int, default=None)
@click.option("--chunk-overlap", type=int, default=None)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.pass_context
def chunk_cmd(
    ctx: click.Context,
    file_path: str | None,
    text: str | None,
    demo: bool,
    chunk_size: int | None,
    chunk_overlap: int | None,
    fmt: str,
) -> None:
    """仅预览切分（不写 store、不 embedding）。"""
    try:
        settings = load_settings(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            store_path=ctx.obj["settings"].store_path,
            mock=ctx.obj["settings"].mock_mode,
        )
        if demo:
            body = DEMO_DOC
            data_source = "demo"
        elif file_path:
            _, body = read_ingest_file(file_path)
            data_source = "file"
        elif text is not None:
            body = text
            data_source = "inline"
        else:
            raise UsageError("需要 --file / --text / --demo")
        pieces = split_with_overlap(body, settings.chunk_size, settings.chunk_overlap)
        _emit(
            _envelope(
                "chunk",
                {
                    "chunk_size": settings.chunk_size,
                    "chunk_overlap": settings.chunk_overlap,
                    "count": len(pieces),
                    "chunks": [{"index": i, "content": p, "chars": len(p)} for i, p in enumerate(pieces)],
                },
                data_source=data_source,
            ),
            fmt=fmt,
            output=None,
        )
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        raise SystemExit(EXIT_USAGE) from exc


def main() -> None:
    try:
        cli(obj={})
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_ERROR
        sys.exit(code)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
