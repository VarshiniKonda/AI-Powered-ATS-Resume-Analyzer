"""Analysis creation, history, details, and report download."""

import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_current_user
from app.db import get_db
from app.ml_engine.matching import analyze_match
from app.ml_engine.semantic import SemanticModelUnavailable
from app.models import (
    AnalysisResult,
    JobDescription,
    MatchedSkill,
    MissingSkill,
    Resume,
    User,
)
from app.schemas import AnalysisCreate, AnalysisRead, AnalysisSummary
from app.services.job_parser import parse_job_description
from app.services.report import build_analysis_pdf
from app.services.resume_parser import DocumentParseError, DocumentTooLargeError, parse_resume_text
from app.services.resume_upload import extract_uploaded_resume

router = APIRouter(prefix="/analyses", tags=["analysis"])


def _summary(analysis: AnalysisResult) -> AnalysisSummary:
    return AnalysisSummary(
        id=analysis.id,
        resume_id=analysis.resume_id,
        resume_filename=analysis.resume.filename,
        job_description_id=analysis.job_description_id,
        job_title=analysis.job_description.title,
        company=analysis.job_description.company,
        overall_score=analysis.overall_score,
        created_at=analysis.created_at,
    )


def _read(analysis: AnalysisResult) -> AnalysisRead:
    return AnalysisRead(
        **_summary(analysis).model_dump(),
        breakdown=analysis.breakdown_json,
        details=analysis.details_json,
    )


def _get_owned_analysis(db: Session, owner_id: int, analysis_id: int) -> AnalysisResult:
    analysis = db.scalar(
        select(AnalysisResult).where(
            AnalysisResult.id == analysis_id,
            AnalysisResult.owner_id == owner_id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return analysis


def _calculate_analysis(
    resume_text: str,
    resume_data: dict[str, Any],
    job_text: str,
    job_data: dict[str, Any],
) -> dict[str, Any]:
    try:
        return analyze_match(resume_text, resume_data, job_text, job_data)
    except SemanticModelUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def _persist_analysis(
    db: Session,
    owner_id: int,
    resume: Resume,
    job: JobDescription,
    result: dict[str, Any],
) -> AnalysisRead:
    db.add_all([resume, job])
    db.flush()
    analysis = AnalysisResult(
        owner_id=owner_id,
        resume_id=resume.id,
        job_description_id=job.id,
        overall_score=result["overall_score"],
        breakdown_json=result["breakdown"],
        details_json=result["details"],
    )
    db.add(analysis)
    db.flush()
    db.add_all(
        [
            MatchedSkill(
                analysis_id=analysis.id,
                skill=item["skill"],
                category=item["category"],
                match_type=item["match_type"],
                evidence=item.get("evidence", ""),
            )
            for item in result["details"]["matched_skills"]
        ]
    )
    db.add_all(
        [
            MissingSkill(
                analysis_id=analysis.id,
                skill=item["skill"],
                category=item["category"],
                explanation=item["explanation"],
            )
            for item in result["details"]["missing_skills"]
        ]
    )
    db.commit()
    db.refresh(analysis)
    return _read(analysis)


@router.post("", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
def create_analysis(
    payload: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisRead:
    resume = db.scalar(
        select(Resume).where(
            Resume.id == payload.resume_id,
            Resume.owner_id == current_user.id,
        )
    )
    job = db.scalar(
        select(JobDescription).where(
            JobDescription.id == payload.job_description_id,
            JobDescription.owner_id == current_user.id,
        )
    )
    if resume is None or job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume or job description not found.",
        )
    result = _calculate_analysis(
        resume.content_text,
        resume.parsed_json,
        job.content_text,
        job.parsed_json,
    )
    return _persist_analysis(db, current_user.id, resume, job, result)


@router.post("/upload", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def analyze_uploaded_resume(
    file: UploadFile = File(...),
    job_description: str = Form(..., min_length=30, max_length=50_000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisRead:
    """Parse and analyze one uploaded resume against manually entered job text."""
    job_text = job_description.strip()
    if len(job_text) < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Job description must contain at least 30 non-whitespace characters.",
        )

    try:
        filename, resume_text = await extract_uploaded_resume(file)
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resume_data = await run_in_threadpool(parse_resume_text, resume_text)
    job_data = await run_in_threadpool(parse_job_description, job_text)
    result = await run_in_threadpool(
        _calculate_analysis,
        resume_text,
        resume_data,
        job_text,
        job_data,
    )
    resume = Resume(
        owner_id=current_user.id,
        filename=filename,
        file_path="",
        content_text=resume_text,
        parsed_json=resume_data,
    )
    job = JobDescription(
        owner_id=current_user.id,
        title=job_data["title"],
        company=None,
        content_text=job_text,
        parsed_json=job_data,
    )
    return _persist_analysis(db, current_user.id, resume, job, result)


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(
    limit: int = Query(default=50, ge=1, le=200),
    resume_id: int | None = None,
    job_description_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnalysisSummary]:
    statement = select(AnalysisResult).where(AnalysisResult.owner_id == current_user.id)
    if resume_id is not None:
        statement = statement.where(AnalysisResult.resume_id == resume_id)
    if job_description_id is not None:
        statement = statement.where(AnalysisResult.job_description_id == job_description_id)
    records = db.scalars(statement.order_by(AnalysisResult.created_at.desc()).limit(limit)).all()
    return [_summary(record) for record in records]


@router.get("/{analysis_id}", response_model=AnalysisRead)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisRead:
    return _read(_get_owned_analysis(db, current_user.id, analysis_id))


@router.get("/{analysis_id}/report")
def download_report(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    analysis = _get_owned_analysis(db, current_user.id, analysis_id)
    filename = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        f"analysis-{analysis.id}-{analysis.job_description.title}",
    ).strip("-")[:100]
    pdf = build_analysis_pdf(
        analysis.job_description.title,
        analysis.job_description.company,
        analysis.resume.filename,
        analysis.overall_score,
        analysis.breakdown_json,
        analysis.details_json,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )