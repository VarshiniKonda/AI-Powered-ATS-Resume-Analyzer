"""Application tracking with per-user status and notes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import AnalysisResult, JobApplication, JobDescription, User
from app.schemas import ApplicationCreate, ApplicationRead, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["job tracking"])


def _read(application: JobApplication, db: Session) -> ApplicationRead:
    latest_score = db.scalar(
        select(AnalysisResult.overall_score)
        .where(
            AnalysisResult.owner_id == application.owner_id,
            AnalysisResult.job_description_id == application.job_description_id,
        )
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    return ApplicationRead(
        id=application.id,
        job_description_id=application.job_description_id,
        job_title=application.job_description.title,
        company=application.job_description.company,
        status=application.status,
        notes=application.notes,
        updated_at=application.updated_at,
        latest_score=latest_score,
    )


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    search: str | None = Query(default=None, max_length=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApplicationRead]:
    statement = select(JobApplication).where(JobApplication.owner_id == current_user.id)
    if search:
        statement = statement.join(JobDescription).where(
            JobDescription.title.ilike(f"%{search.strip()}%")
        )
    if status_filter:
        statement = statement.where(JobApplication.status == status_filter)
    records = db.scalars(statement.order_by(JobApplication.updated_at.desc())).all()
    return [_read(record, db) for record in records]


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    job = db.scalar(
        select(JobDescription).where(
            JobDescription.id == payload.job_description_id,
            JobDescription.owner_id == current_user.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")
    existing = db.scalar(
        select(JobApplication).where(
            JobApplication.job_description_id == job.id,
            JobApplication.owner_id == current_user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This job is already tracked.")
    application = JobApplication(
        owner_id=current_user.id,
        job_description_id=job.id,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return _read(application, db)


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    application = db.scalar(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.owner_id == current_user.id,
        )
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(application, key, value)
    db.commit()
    db.refresh(application)
    return _read(application, db)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    application = db.scalar(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.owner_id == current_user.id,
        )
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    db.delete(application)
    db.commit()
