"""Admin 文件上传 — 图片与知识库文本（txt/md/pdf/docx/html）。"""

import logging
import re
import uuid
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
ALLOWED_KB = {".txt", ".md", ".markdown", ".csv", ".pdf", ".docx", ".html", ".htm"}


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE)
    return base[:120] or "file"


def _decode_text_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=422, detail="decode_failed")


def _extract_html_text(raw: bytes) -> str:
    html = _decode_text_bytes(raw)
    parser = _HtmlTextExtractor()
    parser.feed(html)
    text = parser.text().strip()
    if not text:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise HTTPException(status_code=422, detail="html_empty")
    return text[:200_000]


def _extract_docx_text(raw: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        logger.error("python_docx_missing")
        raise HTTPException(status_code=501, detail="docx_support_unavailable") from exc

    document = Document(BytesIO(raw))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs).strip()
    if not text:
        raise HTTPException(status_code=422, detail="docx_empty")
    return text[:200_000]


def _pdf_text_layer(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        logger.error("pypdf_missing")
        raise HTTPException(status_code=501, detail="pdf_support_unavailable") from exc

    reader = PdfReader(BytesIO(raw))
    pages: list[str] = []
    for page in reader.pages[:80]:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def _pdf_ocr_fallback(raw: bytes) -> str:
    """扫描版 PDF OCR — 需安装 pymupdf、pytesseract、Pillow 及系统 Tesseract。"""
    try:
        import fitz  # pymupdf
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pdf_ocr_deps_missing")
        return ""

    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        pages: list[str] = []
        for page in doc[:20]:
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pages.append(pytesseract.image_to_string(img, lang="chi_sim+eng"))
        return "\n".join(pages).strip()
    except Exception:
        logger.exception("pdf_ocr_failed")
        return ""


def _extract_pdf_text(raw: bytes) -> str:
    text = _pdf_text_layer(raw)
    if text:
        logger.info("pdf_text_layer_ok chars=%s", len(text))
        return text[:200_000]

    settings = get_settings()
    if settings.pdf_ocr_enabled:
        ocr_text = _pdf_ocr_fallback(raw)
        if ocr_text:
            logger.info("pdf_ocr_ok chars=%s", len(ocr_text))
            return ocr_text[:200_000]

    raise HTTPException(
        status_code=422,
        detail=(
            "pdf_scan_needs_ocr: 该 PDF 无文本层。"
            "请设置 PDF_OCR_ENABLED=true 并安装 Tesseract（及 pymupdf/pytesseract/Pillow），"
            "或换用可复制文本的 PDF / DOCX / HTML"
        ),
    )


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
    elif ext == ".docx":
        text = _extract_docx_text(raw)
    elif ext in {".html", ".htm"}:
        text = _extract_html_text(raw)
    else:
        text = _decode_text_bytes(raw)

    logger.info("knowledge_file_read name=%s chars=%s ext=%s", file.filename, len(text), ext)
    return {"filename": _safe_filename(file.filename), "content": text, "character_count": len(text)}
