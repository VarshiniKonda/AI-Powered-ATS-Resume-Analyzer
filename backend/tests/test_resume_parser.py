import pytest

from app.services.resume_parser import (
    DocumentParseError,
    extract_document_text,
    parse_resume_text,
)
from tests.conftest import resume_docx, resume_pdf

SAMPLE_RESUME = """Jordan Rivera
jordan.rivera@example.com
+1 415 555 0184

EXPERIENCE
Software Engineer, Acme
5 years of experience building Python and FastAPI services with PostgreSQL.
Improved request throughput by 25% through measurable query optimization.

EDUCATION
Bachelor of Science in Computer Science, 2019

PROJECTS
Built a Python, React, and scikit-learn project to classify support requests.

CERTIFICATIONS
AWS Certified Developer
"""


@pytest.mark.parametrize(
    ("filename", "content_type", "builder"),
    [
        ("resume.pdf", "application/pdf", resume_pdf),
        (
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            resume_docx,
        ),
    ],
    ids=["pdf", "docx"],
)
def test_extract_pdf_and_docx_resume(filename, content_type, builder) -> None:
    content = builder(SAMPLE_RESUME)
    extracted = extract_document_text(filename, content, content_type)
    parsed = parse_resume_text(extracted)

    assert "Jordan Rivera" in extracted
    assert parsed["email"] == "jordan.rivera@example.com"
    assert parsed["education_level"] == "bachelor"
    assert parsed["experience_years"] == 5
    assert {"Python", "FastAPI", "PostgreSQL", "React"} <= set(parsed["skills"])
    assert parsed["projects"]
    assert parsed["certifications"]


def test_rejects_mismatched_and_unreadable_uploads() -> None:
    with pytest.raises(DocumentParseError):
        extract_document_text("resume.exe", b"not a resume", "application/octet-stream")
    with pytest.raises(DocumentParseError):
        extract_document_text("resume.pdf", b"not a pdf document with enough characters", "application/pdf")


def test_section_extraction_does_not_infer_unavailable_experience() -> None:
    parsed = parse_resume_text("Taylor Example\ntaylor@example.com\nPython developer")
    assert parsed["experience_years"] is None
    assert parsed["education_level"] is None