"""简易 Web：包裹 parse / eval / calibrate，静态页同域托管。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from simsb import __version__
from simsb.config import DEFAULT_FIXTURES, PKG_ROOT, load_settings
from simsb.core.calibrate import run_calibrate
from simsb.core.eval import run_builtin_eval, run_eval
from simsb.core.parser import parse_answer
from simsb.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger("simsb.web")

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Sim-sandbox", version=__version__)


class ParseBody(BaseModel):
    answer_text: str = Field(..., min_length=1)
    brand_list: list[str] = Field(..., min_length=1)
    competitor_brands: list[str] = Field(default_factory=list)
    official_domains: list[str] = Field(default_factory=list)


class EvalBody(BaseModel):
    demo: bool = True
    path: str | None = None
    min_list_acc: float = 0.8


class CalibrateBody(BaseModel):
    demo: bool = True
    open_api_text: str | None = None
    gold_text: str | None = None


def _envelope(module: str, payload: dict[str, Any], *, data_source: str) -> dict[str, Any]:
    return {
        "module": module,
        "version": __version__,
        "data_source": data_source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "service": "simsb-web"}


@app.post("/api/parse")
def api_parse(body: ParseBody) -> dict[str, Any]:
    logger.info(
        "web_parse brands=%s comps=%s text_len=%s",
        body.brand_list,
        body.competitor_brands,
        len(body.answer_text),
    )
    result = parse_answer(
        body.answer_text,
        brand_list=body.brand_list,
        competitor_brands=body.competitor_brands,
        official_domains=body.official_domains or None,
    )
    return _envelope("parse", {"result": result.to_dict()}, data_source="web")


@app.post("/api/eval")
def api_eval(body: EvalBody) -> dict[str, Any]:
    settings = load_settings()
    try:
        if body.demo:
            target = DEFAULT_FIXTURES
            data_source = "demo"
        elif body.path:
            target = Path(body.path)
            data_source = "path"
        else:
            target = settings.fixtures_dir
            data_source = "default"

        if target.is_file():
            payload = run_eval(target)
        elif target.is_dir() and (target / "rank").is_dir():
            payload = run_builtin_eval(target)
        else:
            payload = run_eval(target)
    except Exception as exc:  # noqa: BLE001
        logger.exception("web_eval_failed error=%s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    list_acc = payload.get("list_order_accuracy")
    gate_ok = list_acc is None or list_acc >= body.min_list_acc
    payload["gate"] = {"min_list_order_accuracy": body.min_list_acc, "passed": gate_ok}
    logger.info(
        "web_eval total=%s pass_rate=%s list_acc=%s gate=%s",
        payload.get("total"),
        payload.get("pass_rate"),
        list_acc,
        gate_ok,
    )
    return _envelope("eval", payload, data_source=data_source)


@app.post("/api/calibrate")
def api_calibrate(body: CalibrateBody) -> dict[str, Any]:
    settings = load_settings()
    try:
        if body.demo:
            open_path = PKG_ROOT / "fixtures" / "samples" / "open_api.jsonl"
            gold_path = PKG_ROOT / "fixtures" / "samples" / "gold.jsonl"
            data_source = "demo"
            report = run_calibrate(
                open_api_path=open_path,
                gold_path=gold_path,
                calibration_path=settings.calibration_path,
            )
        else:
            if not body.open_api_text or not body.gold_text:
                raise HTTPException(status_code=400, detail="请提供 open_api_text 与 gold_text，或 demo=true")
            import tempfile

            with tempfile.TemporaryDirectory(prefix="simsb-cal-") as tmp:
                open_path = Path(tmp) / "open_api.jsonl"
                gold_path = Path(tmp) / "gold.jsonl"
                open_path.write_text(body.open_api_text.strip() + "\n", encoding="utf-8")
                gold_path.write_text(body.gold_text.strip() + "\n", encoding="utf-8")
                report = run_calibrate(
                    open_api_path=open_path,
                    gold_path=gold_path,
                    calibration_path=settings.calibration_path,
                )
            data_source = "upload"
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("web_calibrate_failed error=%s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("web_calibrate paired=%s source=%s", report.get("paired"), data_source)
    return _envelope("calibrate", report, data_source=data_source)


@app.get("/")
def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="前端未构建")
    return FileResponse(index_path)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
