#!/usr/bin/env python3
"""清理/迁移存量 GWeb 渠道 → GEOweb。

默认：将 channel_type=gweb_wiki 转为 geoweb，并改写 config_json 字段。
--delete：直接删除 gweb_wiki 渠道（及其未完成的分发任务可选手动处理）。

用法：
  cd geoflow-v3/backend
  PYTHONPATH=. python ../scripts/migrate_gweb_channels_to_geoweb.py
  PYTHONPATH=. python ../scripts/migrate_gweb_channels_to_geoweb.py --delete
  PYTHONPATH=. python ../scripts/migrate_gweb_channels_to_geoweb.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.distribution import DistributionChannel


def _to_geoweb_config(old: dict | None, settings) -> dict:
    cfg = dict(old or {})
    base = (
        str(cfg.get("geoweb_base_url") or cfg.get("gweb_base_url") or cfg.get("endpoint_url") or "")
        .strip()
        .rstrip("/")
    )
    if not base:
        base = (settings.geoweb_base_url or "").rstrip("/")
    token = str(
        cfg.get("geoweb_sync_token") or cfg.get("gweb_sync_secret") or settings.geoweb_sync_token or ""
    ).strip()
    timeout = int(cfg.get("geoweb_timeout_seconds") or cfg.get("gweb_timeout_seconds") or 30)
    out = {
        "domain": cfg.get("domain") or "127.0.0.1",
        "endpoint_url": base,
        "description": cfg.get("description") or "migrated from gweb_wiki",
        "front_mode": cfg.get("front_mode") or "static",
        "template_key": cfg.get("template_key"),
        "geoweb_base_url": base,
        "geoweb_sync_token": token,
        "geoweb_timeout_seconds": timeout,
        "default_page_type": str(cfg.get("default_page_type") or "article"),
    }
    return out


async def run(*, delete: bool, dry_run: bool) -> int:
    settings = get_settings()
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(DistributionChannel).where(DistributionChannel.channel_type == "gweb_wiki")
            )
        ).scalars().all()
        print(f"[migrate] found gweb_wiki channels: {len(rows)}")
        if not rows:
            return 0

        for ch in rows:
            print(f"  - id={ch.id} name={ch.name!r} status={ch.status}")
            if dry_run:
                continue
            if delete:
                await db.delete(ch)
                print(f"    deleted id={ch.id}")
            else:
                ch.channel_type = "geoweb"
                if not str(ch.name or "").lower().startswith("geoweb"):
                    ch.name = f"GEOweb（自 GWeb 迁移）{ch.id}"
                ch.config_json = _to_geoweb_config(
                    ch.config_json if isinstance(ch.config_json, dict) else {},
                    settings,
                )
                print(f"    migrated → geoweb id={ch.id} base={ch.config_json.get('geoweb_base_url')}")

        if not dry_run:
            await db.commit()
            print("[migrate] committed")
        else:
            print("[migrate] dry-run only")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate or delete legacy gweb_wiki channels")
    parser.add_argument("--delete", action="store_true", help="删除而非迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写库")
    args = parser.parse_args()
    return asyncio.run(run(delete=args.delete, dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
