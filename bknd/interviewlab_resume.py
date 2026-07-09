"""
Resume file text extraction for InterviewLab.

Supports plain text, PDF, and DOCX uploads from the setup page.
"""

from __future__ import annotations

import io
from typing import Any


class ResumeParseError(ValueError):
    """Raised when an uploaded resume cannot be parsed."""


SUPPORTED_RESUME_TYPES = (".txt", ".pdf", ".docx")


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ResumeParseError(
            "PDF support requires the pypdf package. Install dependencies from requirements.txt."
        ) from exc

    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise ResumeParseError("Could not extract text from this PDF. Try a text-based PDF or paste your resume instead.")
    return text


def _extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ResumeParseError(
            "Word document support requires python-docx. Install dependencies from requirements.txt."
        ) from exc

    document = Document(io.BytesIO(data))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs).strip()
    if not text:
        raise ResumeParseError("Could not extract text from this Word file. Try PDF, TXT, or paste your resume instead.")
    return text


def extract_resume_text(uploaded_file: Any) -> str:
    """Extract plain text from an uploaded resume file."""
    if uploaded_file is None:
        return ""

    name = (getattr(uploaded_file, "name", "") or "").lower()
    data = uploaded_file.getvalue()
    if not data:
        raise ResumeParseError("The uploaded file is empty.")

    if name.endswith(".txt"):
        return _decode_text(data).strip()
    if name.endswith(".pdf"):
        return _extract_pdf_text(data)
    if name.endswith(".docx"):
        return _extract_docx_text(data)

    raise ResumeParseError("Unsupported file type. Upload a .txt, .pdf, or .docx resume.")


def combine_resume_sources(*, typed_text: str, uploaded_text: str, uploaded_name: str = "") -> str:
    """Merge typed background notes and uploaded resume text."""
    parts: list[str] = []
    uploaded_text = (uploaded_text or "").strip()
    typed_text = (typed_text or "").strip()

    if uploaded_text:
        label = f"Uploaded resume ({uploaded_name})" if uploaded_name else "Uploaded resume"
        parts.append(f"{label}:\n{uploaded_text}")
    if typed_text:
        parts.append(f"Additional background notes:\n{typed_text}")

    return "\n\n".join(parts).strip()
