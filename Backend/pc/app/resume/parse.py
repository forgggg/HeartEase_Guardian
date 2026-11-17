from __future__ import annotations

import io
import re

from ..errors import AppError

MAX_UPLOAD_MB = 8


def extract_text(filename: str, data: bytes) -> str:
    """支持文本型 PDF / DOCX；扫描件与图片本期不支持。"""
    name = (filename or "").lower()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise AppError(422, "FILE_TOO_LARGE", f"文件超过 {MAX_UPLOAD_MB}MB 限制")

    if name.endswith(".pdf"):
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise AppError(422, "PDF_PARSE_FAILED", f"PDF 解析失败：{exc}")
    elif name.endswith(".docx"):
        from docx import Document

        try:
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            raise AppError(422, "DOCX_PARSE_FAILED", f"DOCX 解析失败：{exc}")
    else:
        raise AppError(
            415,
            "UNSUPPORTED_FILE_TYPE",
            "仅支持文本型 .pdf / .docx",
            "图片与扫描件本期不支持",
        )

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 20:
        raise AppError(
            422,
            "SCANNED_OR_EMPTY",
            "未解析到有效文本",
            "可能是扫描件/图片型 PDF，本期不支持",
        )
    return text
