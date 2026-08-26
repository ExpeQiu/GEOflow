"""技术 IP YAML 批量导入。"""

import logging

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tech_ip import TechIpAsset

logger = logging.getLogger(__name__)


class TechYamlImportBody(BaseModel):
    yaml_text: str = Field(min_length=1)


async def import_tech_assets_yaml(db: AsyncSession, body: TechYamlImportBody) -> dict:
    try:
        data = yaml.safe_load(body.yaml_text)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"invalid_yaml:{exc}") from exc

    rows = data if isinstance(data, list) else data.get("assets", []) if isinstance(data, dict) else []
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=422, detail="yaml_must_be_asset_list")

    created = 0
    updated = 0
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        action = await upsert_tech_asset_row(db, raw)
        if action == "created":
            created += 1
        elif action == "updated":
            updated += 1
    await db.flush()
    logger.info("tech_yaml_imported created=%s updated=%s", created, updated)
    return {"created": created, "updated": updated}


async def upsert_tech_asset_row(db: AsyncSession, raw: dict) -> str | None:
    ip_id = str(raw.get("ip_id") or raw.get("id") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not ip_id or not name:
        return None
    existing = (await db.execute(select(TechIpAsset).where(TechIpAsset.ip_id == ip_id))).scalars().first()
    payload = {
        "name": name,
        "mind_tag": str(raw.get("mind_tag") or ""),
        "ip_layer": str(raw.get("ip_layer") or ""),
        "wiki_type": str(raw.get("wiki_type") or "concept"),
        "wiki_slug": raw.get("wiki_slug"),
        "priority": int(raw.get("priority") or 100),
        "description": str(raw.get("description") or ""),
        "meta_json": raw.get("meta_json") if isinstance(raw.get("meta_json"), dict) else raw,
        "status": str(raw.get("status") or "active"),
    }
    if existing:
        for k, v in payload.items():
            setattr(existing, k, v)
        return "updated"
    db.add(TechIpAsset(ip_id=ip_id, **payload))
    return "created"
