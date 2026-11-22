import pytest
from sqlalchemy import select

from app.models import JobDescription, MatchedSkill, MissingSkill, Resume
from tests.conftest import TestSession, register_user, resume_docx, resume_pdf

RESUME_TEXT = """Jordan Rivera
jordan@example.com
EXPERIENCE
Python FastAPI backend engineer with 5 years experience.
EDUCATION
Bachelor of Science in Computer Science
PROJECTS
Python forecasting project using scikit-learn for demand analysis.
"""

DIRECT_JOB_DESCRIPTION = """Senior Python Engineer
Required skills: Python, FastAPI, PostgreSQL, and AWS.
Preferred skills: Kubernetes.
Minimum 4 years of experience. Bachelor's degree required.
Responsibilities: Build reliable APIs and data services.
"""


def _headers(client, email="jordan@example.com"):
    account = register_user(client, email)
    return {"Authorization": f"Bearer {account['access_token']}"}


def test_resume_upload_and_records_are_user_scoped(client) -> None:
    owner_headers = _headers(client)
    other_headers = _headers(client, "other@example.com")
    upload = client.post(
        "/api/resumes",
        headers=owner_headers,
        files={"file": ("jordan.pdf", resume_pdf(RESUME_TEXT), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    resume_id = upload.json()["id"]
    assert upload.json()["parsed_data"]["skills"]

    assert client.get("/api/resumes", headers=owner_headers).json()[0]["id"] == resume_id
    assert client.get(f"/api/resumes/{resume_id}", headers=other_headers).status_code == 404
    assert client.delete(f"/api/resumes/{resume_id}", headers=owner_headers).status_code == 204
    assert client.get("/api/resumes", headers=owner_headers).json() == []


def test_job_tracking_analysis_and_reports(client) -> None:
    headers = _headers(client)
    resume = client.post(
        "/api/resumes",
        headers=headers,
        files={"file": ("jordan.pdf", resume_pdf(RESUME_TEXT), "application/pdf")},
    ).json()
    job_response = client.post(
        "/api/jobs",
        headers=headers,
        json={
            "title": "Senior Python Engineer",
            "company": "Example Co",
            "content_text": (
                "Senior Python Engineer. Required Python, FastAPI, and PostgreSQL. "
                "Minimum 4 years of experience. Bachelor's degree required. "
                "Build and maintain reliable software projects. Nice to have: Kubernetes."
            ),
        },
    )
    assert job_response.status_code == 201, job_response.text
    job = job_response.json()
    assert "Python" in job["parsed_data"]["required_skills"]

    # This integration test uses the real configured Sentence Transformer model.
    analysis_response = client.post(
        "/api/analyses",
        headers=headers,
        json={"resume_id": resume["id"], "job_description_id": job["id"]},
    )
    assert analysis_response.status_code == 201, analysis_response.text
    analysis = analysis_response.json()
    assert 0 <= analysis["overall_score"] <= 100
    assert analysis["details"]["semantic_similarity_percentage"] is not None
    assert any(item["skill"] == "Python" for item in analysis["details"]["matched_skills"])
    missing_required = analysis["details"]["missing_required_skills"]
    assert any(item["skill"] == "PostgreSQL" and item["explanation"] for item in missing_required)
    assert any(item["skill"] == "Kubernetes" for item in analysis["details"]["missing_preferred_skills"])
    with TestSession() as session:
        assert session.scalar(select(MatchedSkill.id).where(MatchedSkill.analysis_id == analysis["id"]))
        assert session.scalar(select(MissingSkill.id).where(MissingSkill.analysis_id == analysis["id"]))
    assert client.get("/api/analyses", headers=headers).json()[0]["id"] == analysis["id"]
    assert client.get(f"/api/analyses/{analysis['id']}", headers=headers).status_code == 200

    pdf = client.get(f"/api/analyses/{analysis['id']}/report", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")

    dashboard = client.get("/api/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_analyses"] == 1

    tracked = client.post(
        "/api/applications",
        headers=headers,
        json={"job_description_id": job["id"], "status": "Applied", "notes": "Applied online"},
    )
    assert tracked.status_code == 201, tracked.text
    assert tracked.json()["latest_score"] == analysis["overall_score"]
    application_id = tracked.json()["id"]
    assert client.patch(
        f"/api/applications/{application_id}",
        headers=headers,
        json={"status": "Interview"},
    ).json()["status"] == "Interview"
    assert client.get("/api/applications?status=Interview", headers=headers).json()[0]["id"] == application_id
    assert client.delete(f"/api/applications/{application_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/resumes/{resume['id']}", headers=headers).status_code == 204
    assert client.get("/api/analyses", headers=headers).json() == []


def test_upload_rejects_invalid_and_oversized_files(client) -> None:
    headers = _headers(client)
    invalid = client.post(
        "/api/resumes",
        headers=headers,
        files={"file": ("resume.exe", b"not a document", "application/octet-stream")},
    )
    assert invalid.status_code == 422
    oversized = client.post(
        "/api/resumes",
        headers=headers,
        files={"file": ("large.pdf", b"%PDF-1.7" + b"x" * (10 * 1024 * 1024), "application/pdf")},
    )
    assert oversized.status_code == 413


@pytest.mark.parametrize(
    ("filename", "content_type", "builder"),
    [
        ("direct-resume.pdf", "application/pdf", resume_pdf),
        (
            "direct-resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            resume_docx,
        ),
    ],
    ids=["pdf", "docx"],
)
def test_direct_analyzer_upload_persists_real_inputs_and_history(
    client,
    filename,
    content_type,
    builder,
) -> None:
    headers = _headers(client)
    response = client.post(
        "/api/analyses/upload",
        headers=headers,
        data={"job_description": DIRECT_JOB_DESCRIPTION},
        files={"file": (filename, builder(RESUME_TEXT), content_type)},
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["resume_filename"] == filename
    assert 0 <= result["overall_score"] <= 100
    assert result["details"]["matched_keywords"]
    assert result["details"]["resume_strengths"]
    assert result["details"]["areas_to_improve"]
    assert any(item["skill"] == "Python" for item in result["details"]["matched_skills"])
    assert any(item["skill"] == "PostgreSQL" for item in result["details"]["missing_required_skills"])
    assert client.get("/api/analyses", headers=headers).json()[0]["id"] == result["id"]

    with TestSession() as session:
        resume = session.scalar(select(Resume).where(Resume.id == result["resume_id"]))
        job = session.scalar(
            select(JobDescription).where(JobDescription.id == result["job_description_id"])
        )
        assert resume is not None
        assert RESUME_TEXT.splitlines()[0] in resume.content_text
        assert resume.file_path == ""
        assert job is not None
        assert job.content_text == DIRECT_JOB_DESCRIPTION.strip()

    other_headers = _headers(client, "other@example.com")
    assert client.get("/api/analyses", headers=other_headers).json() == []
    assert client.get("/api/resumes", headers=other_headers).json() == []
    assert client.get("/api/jobs", headers=other_headers).json() == []


def test_direct_analyzer_rejects_invalid_inputs_without_saving_records(client) -> None:
    headers = _headers(client)
    pdf = resume_pdf(RESUME_TEXT)
    short_description = client.post(
        "/api/analyses/upload",
        headers=headers,
        data={"job_description": "Too short"},
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert short_description.status_code == 422

    whitespace_description = client.post(
        "/api/analyses/upload",
        headers=headers,
        data={"job_description": " " * 40},
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert whitespace_description.status_code == 422
    assert "non-whitespace" in whitespace_description.json()["detail"]

    invalid_file = client.post(
        "/api/analyses/upload",
        headers=headers,
        data={"job_description": DIRECT_JOB_DESCRIPTION},
        files={"file": ("resume.exe", b"not a resume", "application/octet-stream")},
    )
    assert invalid_file.status_code == 422

    oversized_file = client.post(
        "/api/analyses/upload",
        headers=headers,
        data={"job_description": DIRECT_JOB_DESCRIPTION},
        files={
            "file": (
                "large.pdf",
                b"%PDF-1.7" + b"x" * (10 * 1024 * 1024),
                "application/pdf",
            )
        },
    )
    assert oversized_file.status_code == 413
    assert client.get("/api/resumes", headers=headers).json() == []
    assert client.get("/api/jobs", headers=headers).json() == []
    assert client.get("/api/analyses", headers=headers).json() == []