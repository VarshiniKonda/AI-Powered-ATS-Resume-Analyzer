"""User-scoped job description management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import JobDescription, User
from app.schemas import JobCreate, JobRead, JobUpdate
from app.services.job_parser import parse_job_description

router = APIRouter(prefix="/jobs", tags=["job descriptions"])


def _job_read(job: JobDescription) -> JobRead:
    return JobRead(
        id=job.id,
        title=job.title,
        company=job.company,
        content_text=job.content_text,
        parsed_data=job.parsed_json,
        created_at=job.created_at,
    )


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRead:
    parsed = parse_job_description(
        payload.content_text,
        title=payload.title,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
    )
    job = JobDescription(
        owner_id=current_user.id,
        title=parsed["title"],
        company=payload.company.strip() if payload.company else None,
        content_text=payload.content_text,
        parsed_json=parsed,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get("", response_model=list[JobRead])
def list_jobs(
    search: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobRead]:
    statement = select(JobDescription).where(JobDescription.owner_id == current_user.id)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                JobDescription.title.ilike(term),
                JobDescription.company.ilike(term),
                JobDescription.content_text.ilike(term),
            )
        )
    records = db.scalars(statement.order_by(JobDescription.created_at.desc())).all()
    return [_job_read(job) for job in records]


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRead:
    job = db.scalar(
        select(JobDescription).where(
            JobDescription.id == job_id, JobDescription.owner_id == current_user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")
    return _job_read(job)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRead:
    job = db.scalar(
        select(JobDescription).where(
            JobDescription.id == job_id, JobDescription.owner_id == current_user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")
    changes = payload.model_dump(exclude_unset=True)
    title = changes.get("title") or job.title
    required = changes.get("required_skills", job.parsed_json.get("required_skills", []))
    preferred = changes.get("preferred_skills", job.parsed_json.get("preferred_skills", []))
    if (
        changes.get("title") is not None
        or changes.get("content_text") is not None
        or "required_skills" in changes
        or "preferred_skills" in changes
    ):
        parsed = parse_job_description(
            changes.get("content_text", job.content_text),
            title=title,
            required_skills=required or [],
            preferred_skills=preferred or [],
        )
        job.parsed_json = parsed
    if "title" in changes and changes["title"] is not None:
        job.title = changes["title"].strip()
        job.parsed_json = {**job.parsed_json, "title": job.title}
    if "company" in changes:
        job.company = changes["company"].strip() if changes["company"] else None
    if "content_text" in changes and changes["content_text"] is not None:
        job.content_text = changes["content_text"].strip()
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    job = db.scalar(
        select(JobDescription).where(
            JobDescription.id == job_id, JobDescription.owner_id == current_user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")
    db.delete(job)
    db.commit()