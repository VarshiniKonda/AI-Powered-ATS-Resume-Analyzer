"""User-scoped resume upload, listing, detail, and deletion."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import Resume, User
from app.schemas import ResumeRead
from app.services.resume_parser import (
    DocumentParseError,
    DocumentTooLargeError,
    parse_resume_text,
)
from app.services.resume_upload import extract_uploaded_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _resume_read(resume: Resume) -> ResumeRead:
    return ResumeRead(
        id=resume.id,
        filename=resume.filename,
        parsed_data=resume.parsed_json,
        created_at=resume.created_at,
    )


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeRead:
    try:
        filename, text = await extract_uploaded_resume(file)
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resume = Resume(
        owner_id=current_user.id,
        filename=filename,
        file_path="",
        content_text=text,
        parsed_json=parse_resume_text(text),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return _resume_read(resume)


@router.get("", response_model=list[ResumeRead])
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResumeRead]:
    records = db.scalars(
        select(Resume).where(Resume.owner_id == current_user.id).order_by(Resume.created_at.desc())
    ).all()
    return [_resume_read(resume) for resume in records]


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeRead:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.owner_id == current_user.id)
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return _resume_read(resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.owner_id == current_user.id)
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    db.delete(resume)
    db.commit()