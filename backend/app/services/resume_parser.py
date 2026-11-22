"""Safe PDF/DOCX extraction and structured resume parsing."""

import io
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

import fitz
from docx import Document

from app.ml_engine.skills import extract_skill_occurrences

SECTION_HEADINGS = {
    "experience": {"experience", "work experience", "employment", "professional experience"},
    "education": {"education", "academic background", "qualifications"},
    "projects": {"projects", "selected projects", "personal projects", "project experience"},
    "certifications": {"certifications", "certificates", "licenses", "licenses & certifications"},
    "skills": {"skills", "technical skills", "core competencies", "tools"},
}
HEADING_LINE = re.compile(r"^[A-Z][A-Z0-9 &/,+()'’-]{1,60}:?$")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
YEAR_RANGE_PATTERN = re.compile(
    r"\b(19\d{2}|20\d{2})\s*(?:-|–|—|to)\s*(present|current|19\d{2}|20\d{2})\b",
    re.IGNORECASE,
)
EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?"
    r"(?:(?:relevant|professional|work)\s+)?experience\b",
    re.IGNORECASE,
)
EDUCATION_LEVELS = (
    ("doctorate", re.compile(r"\b(ph\.?d\.?|doctorate|doctoral)\b", re.I)),
    ("master", re.compile(r"\b(master(?:'s)?|m\.?s\.?|m\.?sc\.?|mba)\b", re.I)),
    ("bachelor", re.compile(r"\b(bachelor(?:'s)?|b\.?s\.?|b\.?sc\.?|b\.?a\.?|b\.?e\.?)\b", re.I)),
    ("associate", re.compile(r"\b(associate'?s|a\.?a\.?|a\.?s\.?)\b", re.I)),
    ("high_school", re.compile(r"\b(high school|secondary school|ged)\b", re.I)),
)


class DocumentParseError(ValueError):
    """A user-provided document is invalid, unsupported, or unreadable."""


class DocumentTooLargeError(DocumentParseError):
    """A user-provided document exceeds the configured upload limit."""


def clean_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("\x00", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def extract_document_text(filename: str, content: bytes, content_type: str | None) -> str:
    if not content:
        raise DocumentParseError("The uploaded file is empty.")
    suffix = PurePath(filename).suffix.casefold()
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
        "application/zip",
    }
    if suffix not in {".pdf", ".docx"}:
        raise DocumentParseError("Only PDF and DOCX resumes are supported.")
    if content_type and content_type not in allowed_types:
        raise DocumentParseError("The uploaded file has an unsupported media type.")

    try:
        if suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise DocumentParseError("The uploaded file is not a valid PDF.")
            with fitz.open(stream=content, filetype="pdf") as document:
                if document.is_encrypted:
                    raise DocumentParseError("Password-protected PDFs cannot be processed.")
                if document.page_count > 100:
                    raise DocumentParseError("PDF resumes may contain at most 100 pages.")
                text = "\n".join(page.get_text("text") for page in document)
        else:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()
                if (
                    len(entries) > 2000
                    or sum(entry.file_size for entry in entries) > 25_000_000
                    or "word/document.xml" not in archive.namelist()
                ):
                    raise DocumentParseError("The DOCX package is invalid or too large.")
            document = Document(io.BytesIO(content))
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                paragraphs.extend(cell.text for row in table.rows for cell in row.cells)
            text = "\n".join(paragraphs)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("The uploaded document could not be parsed.") from exc

    cleaned = clean_text(text)
    if len(cleaned) < 30:
        raise DocumentParseError(
            "The document contains too little extractable text. Scanned PDFs need OCR."
        )
    if len(cleaned) > 1_000_000:
        raise DocumentParseError("The extracted resume text exceeds the processing limit.")
    return cleaned


def _split_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        heading = line.strip().rstrip(":").casefold()
        matched = next((name for name, headings in SECTION_HEADINGS.items() if heading in headings), None)
        if matched:
            current = matched
            sections.setdefault(current, [])
            continue
        if current is None and HEADING_LINE.match(line.strip()):
            continue
        if current:
            sections[current].append(line)
    return {
        section: "\n".join(contents).strip()
        for section, contents in sections.items()
        if "\n".join(contents).strip()
    }


def _estimate_experience_years(text: str) -> float | None:
    explicit = EXPERIENCE_PATTERN.search(text)
    if explicit:
        return float(explicit.group(1))

    current_year = datetime.now(timezone.utc).year
    ranges: list[tuple[int, int]] = []
    for start, end_value in YEAR_RANGE_PATTERN.findall(text):
        start_year = int(start)
        end_year = current_year if end_value.casefold() in {"present", "current"} else int(end_value)
        if 1950 <= start_year <= end_year <= current_year:
            ranges.append((start_year, end_year))
    if not ranges:
        return None

    ranges.sort()
    merged: list[list[int]] = []
    for start_year, end_year in ranges:
        if merged and start_year <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end_year)
        else:
            merged.append([start_year, end_year])
    total_months = sum((end - start) * 12 for start, end in merged)
    return round(total_months / 12, 1) if total_months >= 12 else None


def _education_level(text: str) -> str | None:
    for level, pattern in EDUCATION_LEVELS:
        if pattern.search(text):
            return level
    return None


def parse_resume_text(text: str) -> dict[str, Any]:
    cleaned = clean_text(text)
    sections = _split_sections(cleaned)
    email_match = EMAIL_PATTERN.search(cleaned)
    phone_match = PHONE_PATTERN.search(cleaned)
    nonempty_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    candidate_name = next(
        (
            line
            for line in nonempty_lines[:5]
            if len(line) <= 80 and not EMAIL_PATTERN.search(line) and not re.search(r"\d{4}", line)
        ),
        None,
    )
    skills = extract_skill_occurrences(cleaned)
    education_text = sections.get("education", "")
    education_level = _education_level(education_text or cleaned)
    return {
        "name": candidate_name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "skills": [item.skill for item in skills],
        "skill_evidence": [{"skill": item.skill, "evidence": item.context} for item in skills],
        "education": education_text or None,
        "education_level": education_level,
        "experience": sections.get("experience"),
        "experience_years": _estimate_experience_years(sections.get("experience", "")),
        "certifications": sections.get("certifications"),
        "projects": sections.get("projects"),
        "sections": sections,
        "extraction_notes": [
            "Name and contact details are heuristic extractions; review them for accuracy."
        ],
    }