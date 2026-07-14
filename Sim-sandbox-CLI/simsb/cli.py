"""simsb CLI — 探针仿真沙箱命令面。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from simsb import __version__
from simsb.config import DEFAULT_FIXTURES, PKG_ROOT, load_settings
from simsb.core.calibrate import run_calibrate
from simsb.core.eval import run_builtin_eval, run_eval
from simsb.core.parser import parse_answer
from simsb.utils.errors import EXIT_ERROR, EXIT_OK, EXIT_USAGE, FixtureError, UsageError
from simsb.utils.logger import get_logger, setup_logging

logger = get_logger("simsb.cli")


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
    if not isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, indent=2)
    module = data.get("module")
    if module == "eval":
        lines = [
            f"metric_kind={data.get('metric_kind')} total={data.get('total')} "
            f"passed={data.get('passed')} pass_rate={data.get('pass_rate')}",
            f"list_order_accuracy={data.get('list_order_accuracy')} "
            f"(n={data.get('list_order_cases')})",
            "-" * 56,
        ]
        for r in data.get("results") or []:
            mark = "OK" if r.get("passed") else "FAIL"
            lines.append(f"[{mark}] {r.get('id')} fields={r.get('field_ok')}")
        return "\n".join(lines)
    if module == "parse":
        p = data.get("result") or {}
        return (
            f"mentioned={p.get('mentioned')} rank={p.get('brand_rank')} "
            f"method={p.get('rank_method')} conf={p.get('confidence')}\n"
            f"evidence={p.get('evidence_level')}/{p.get('match_type')} "
            f"urls={len(p.get('urls') or [])}\n"
            f"order={p.get('mention_order')}\n"
            f"snippet={p.get('snippet')}"
        )
    if module == "calibrate":
        return (
            f"paired={data.get('paired')} "
            f"mean_mention_delta={data.get('mean_mention_delta')} "
            f"mean_rank_delta={data.get('mean_rank_delta')}\n"
            f"suggestions={json.dumps(data.get('suggestions'), ensure_ascii=False)}"
        )
    return json.dumps(data, ensure_ascii=False, indent=2)


def _envelope(module: str, payload: dict[str, Any], *, data_source: str) -> dict[str, Any]:
    return {
        "module": module,
        "version": __version__,
        "data_source": data_source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }


@click.group()
@click.version_option(__version__, prog_name="simsb")
@click.option("--verbose", "-v", is_flag=True, help="DEBUG 日志")
@click.option("--quiet", "-q", is_flag=True, help="仅警告及以上")
@click.option("--fixtures", "fixtures_dir", default=None, help="夹具根目录")
@click.pass_context
def main(ctx: click.Context, verbose: bool, quiet: bool, fixtures_dir: str | None) -> None:
    """Sim-sandbox-CLI：探针答文解析 / 夹具评测 / 金标偏移对照。"""
    setup_logging(verbose=verbose, quiet=quiet)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = load_settings(fixtures_dir=fixtures_dir)


@main.command("parse")
@click.option("--text", "answer_text", default=None, help="答文正文")
@click.option("--file", "answer_file", type=click.Path(exists=True, dir_okay=False), default=None)
@click.option("--brands", required=True, help="监控品牌，逗号分隔")
@click.option("--competitors", default="", help="竞品，逗号分隔")
@click.option("--official-domains", default="", help="官网域名，逗号分隔")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--output", "-o", default=None, help="写入文件")
@click.pass_context
def cmd_parse(
    ctx: click.Context,
    answer_text: str | None,
    answer_file: str | None,
    brands: str,
    competitors: str,
    official_domains: str,
    fmt: str,
    output: str | None,
) -> None:
    """解析单条答文（Rank v2 + Citation L0/L1）。"""
    try:
        if answer_file:
            text = Path(answer_file).read_text(encoding="utf-8")
            source = "file"
        elif answer_text is not None:
            text = answer_text
            source = "flag"
        else:
            raise UsageError("请提供 --text 或 --file")
        brand_list = [b.strip() for b in brands.split(",") if b.strip()]
        comps = [b.strip() for b in competitors.split(",") if b.strip()]
        official = [d.strip() for d in official_domains.split(",") if d.strip()]
        result = parse_answer(
            text,
            brand_list=brand_list,
            competitor_brands=comps,
            official_domains=official or None,
        )
        logger.info(
            "parse_done mentioned=%s rank=%s method=%s evidence=%s",
            result.mentioned,
            result.brand_rank,
            result.rank_method,
            result.evidence_level,
        )
        _emit(
            _envelope("parse", {"result": result.to_dict()}, data_source=source),
            fmt=fmt,
            output=output,
        )
    except UsageError as exc:
        click.echo(f"用法错误: {exc}", err=True)
        sys.exit(EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001
        logger.exception("parse_failed error=%s", exc)
        click.echo(f"错误: {exc}", err=True)
        sys.exit(EXIT_ERROR)


@main.command("eval")
@click.argument("path", required=False, default=None)
@click.option("--demo", is_flag=True, help="评测内置 fixtures/")
@click.option("--min-list-acc", default=0.8, show_default=True, type=float, help="list_order 准确率门槛")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--output", "-o", default=None)
@click.pass_context
def cmd_eval(
    ctx: click.Context,
    path: str | None,
    demo: bool,
    min_list_acc: float,
    fmt: str,
    output: str | None,
) -> None:
    """对夹具跑解析评测（L1 仿真沙箱主验收）。"""
    settings = ctx.obj["settings"]
    try:
        if demo:
            target = DEFAULT_FIXTURES
            data_source = "demo"
        elif path:
            target = Path(path)
            data_source = "path"
        else:
            target = settings.fixtures_dir
            data_source = "default"

        # 默认夹具根目录时只评测 rank/ + citation/（跳过 samples 对照样本）
        if target.is_dir() and (target / "rank").is_dir():
            results_payload = run_builtin_eval(target)
        else:
            results_payload = run_eval(target)

        list_acc = results_payload.get("list_order_accuracy")
        gate_ok = list_acc is None or list_acc >= min_list_acc
        results_payload["gate"] = {
            "min_list_order_accuracy": min_list_acc,
            "passed": gate_ok,
        }
        logger.info(
            "eval_cli total=%s pass_rate=%s list_acc=%s gate=%s",
            results_payload.get("total"),
            results_payload.get("pass_rate"),
            list_acc,
            gate_ok,
        )
        _emit(_envelope("eval", results_payload, data_source=data_source), fmt=fmt, output=output)
        if not gate_ok or results_payload.get("failed", 0) > 0:
            sys.exit(EXIT_ERROR)
    except (FixtureError, UsageError) as exc:
        click.echo(f"用法/夹具错误: {exc}", err=True)
        sys.exit(EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001
        logger.exception("eval_failed error=%s", exc)
        click.echo(f"错误: {exc}", err=True)
        sys.exit(EXIT_ERROR)


@main.command("calibrate")
@click.option("--open-api", "open_api", default=None, type=click.Path(exists=True, dir_okay=False))
@click.option("--gold", default=None, type=click.Path(exists=True, dir_okay=False))
@click.option("--demo", is_flag=True, help="使用 fixtures/samples 演示对照")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--output", "-o", default=None)
@click.pass_context
def cmd_calibrate(
    ctx: click.Context,
    open_api: str | None,
    gold: str | None,
    demo: bool,
    fmt: str,
    output: str | None,
) -> None:
    """同题 Open-API vs 金标偏移报告（只出建议，不改写 KPI）。"""
    settings = ctx.obj["settings"]
    try:
        if demo:
            open_path = PKG_ROOT / "fixtures" / "samples" / "open_api.jsonl"
            gold_path = PKG_ROOT / "fixtures" / "samples" / "gold.jsonl"
            data_source = "demo"
        else:
            if not open_api or not gold:
                raise UsageError("请提供 --open-api 与 --gold，或使用 --demo")
            open_path = Path(open_api)
            gold_path = Path(gold)
            data_source = "path"
        report = run_calibrate(
            open_api_path=open_path,
            gold_path=gold_path,
            calibration_path=settings.calibration_path,
        )
        _emit(_envelope("calibrate", report, data_source=data_source), fmt=fmt, output=output)
    except (FixtureError, UsageError) as exc:
        click.echo(f"用法错误: {exc}", err=True)
        sys.exit(EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001
        logger.exception("calibrate_failed error=%s", exc)
        click.echo(f"错误: {exc}", err=True)
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
