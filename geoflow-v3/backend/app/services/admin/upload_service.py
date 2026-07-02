"""Admin 文件上传 — 图片与知识库文本。"""

import logging
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
ALLOWED_KB = {".txt", ".md", ".markdown", ".csv", ".pdf"}


def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE)
    return base[:120] or "file"


def _extract_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        logger.error("pypdf_missing")
        raise HTTPException(status_code=501, detail="pdf_support_unavailable") from exc

    import io

    reader = PdfReader(io.BytesIO(raw))
    pages: list[str] = []
    for page in reader.pages[:80]:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        raise HTTPException(status_code=422, detail="pdf_empty_or_unreadable")
    return text[:200_000]


def _ensure_dir(subdir: str) -> Path:
    root = Path(get_settings().upload_path).resolve()
    target = (root / subdir).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail="invalid_upload_path")
    target.mkdir(parents=True, exist_ok=True)
    return target


async def save_image_upload(library_id: int, file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(status_code=422, detail="missing_filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE:
        raise HTTPException(status_code=422, detail="unsupported_image_type")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="file_too_large")

    dest_dir = _ensure_dir(f"images/lib_{library_id}")
    stored = f"{uuid.uuid4().hex}{ext}"
    dest_path = dest_dir / stored
    dest_path.write_bytes(content)

    rel_path = str(dest_path.relative_to(Path(get_settings().upload_path).resolve()))
    logger.info("image_uploaded library_id=%s path=%s size=%s", library_id, rel_path, len(content))
    return {
        "original_name": _safe_filename(file.filename),
        "file_path": rel_path,
        "mime_type": file.content_type or "",
        "file_size": len(content),
    }


async def read_knowledge_upload(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(status_code=422, detail="missing_filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_KB:
        raise HTTPException(status_code=422, detail="unsupported_kb_file_type")

    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="file_too_large")

    if ext == ".pdf":
        text = _extract_pdf_text(raw)
    else:
        text = ""
        for encoding in ("utf-8", "gbk", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if not text:
            raise HTTPException(status_code=422, detail="decode_failed")

    logger.info("knowledge_file_read name=%s chars=%s ext=%s", file.filename, len(text), ext)
    return {"filename": _safe_filename(file.filename), "content": text, "character_count": len(text)}
