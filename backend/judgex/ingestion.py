from pathlib import Path
from io import BytesIO
import re

from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader
import pypdfium2 as pdfium


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|github_pat|gho|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[:=]\s*(['\"]?)[^\s,'\";]{8,}\2"),
]


def redact_secrets(text: str) -> tuple[str, int]:
    redacted = text
    count = 0
    for pattern in SECRET_PATTERNS:
        redacted, matches = pattern.subn("[REDACTED SECRET]", redacted)
        count += matches
    return redacted, count


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if suffix == ".docx":
        doc = DocxDocument(path)
        parts = [paragraph.text for paragraph in doc.paragraphs]
        for table in doc.tables:
            parts.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        return "\n".join(parts)
    if suffix == ".pptx":
        deck = Presentation(path)
        return "\n".join(shape.text for slide in deck.slides for shape in slide.shapes if getattr(shape, "has_text_frame", False))
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def chunk_text(text: str, size: int = 1500, overlap: int = 220) -> list[str]:
    clean = re.sub(r"[ \t]+", " ", text.replace("\x00", " ")).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + size, len(clean))
        if end < len(clean):
            boundary = max(clean.rfind("\n", start + size // 2, end), clean.rfind(". ", start + size // 2, end))
            if boundary > start:
                end = boundary + 1
        excerpt = clean[start:end].strip()
        if excerpt:
            chunks.append(excerpt)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def render_pdf_pages(path: Path, max_pages: int = 20) -> list[bytes]:
    document = pdfium.PdfDocument(path)
    images: list[bytes] = []
    for index in range(min(len(document), max_pages)):
        page = document[index]
        bitmap = page.render(scale=1.35)
        buffer = BytesIO()
        bitmap.to_pil().convert("RGB").save(buffer, format="JPEG", quality=82, optimize=True)
        images.append(buffer.getvalue())
        page.close()
    document.close()
    return images
