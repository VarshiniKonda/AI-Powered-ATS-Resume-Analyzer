from tests.conftest import register_user, resume_pdf


def _headers(client, email: str) -> dict[str, str]:
    account = register_user(client, email)
    return {"Authorization": f"Bearer {account['access_token']}"}


def test_job_and_resume_ownership_and_tracker_cascade(client) -> None:
    owner_headers = _headers(client, "owner@example.com")
    other_headers = _headers(client, "other@example.com")
    resume = client.post(
        "/api/resumes",
        headers=owner_headers,
        files={
            "file": (
                "owner.pdf",
                resume_pdf("Alex Owner\nalex@example.com\nPython FastAPI software engineer"),
                "application/pdf",
            )
        },
    ).json()
    job = client.post(
        "/api/jobs",
        headers=owner_headers,
        json={
            "title": "API Engineer",
            "content_text": "API Engineer. Required Python and FastAPI experience building APIs.",
        },
    ).json()

    assert client.get(f"/api/jobs/{job['id']}", headers=other_headers).status_code == 404
    assert client.get(f"/api/resumes/{resume['id']}", headers=other_headers).status_code == 404
    assert client.post(
        "/api/analyses",
        headers=other_headers,
        json={"resume_id": resume["id"], "job_description_id": job["id"]},
    ).status_code == 404

    tracked = client.post(
        "/api/applications",
        headers=owner_headers,
        json={"job_description_id": job["id"]},
    )
    assert tracked.status_code == 201
    updated = client.patch(
        f"/api/jobs/{job['id']}",
        headers=owner_headers,
        json={
            "title": "Senior API Engineer",
            "required_skills": ["Python", "FastAPI"],
            "content_text": "Senior API Engineer. Required Python and FastAPI experience building APIs.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Senior API Engineer"
    assert updated.json()["parsed_data"]["required_skills"] == ["FastAPI", "Python"]

    assert client.get("/api/jobs?search=Senior", headers=owner_headers).json()[0]["id"] == job["id"]
    assert client.delete(f"/api/jobs/{job['id']}", headers=owner_headers).status_code == 204
    assert client.get("/api/applications", headers=owner_headers).json() == []