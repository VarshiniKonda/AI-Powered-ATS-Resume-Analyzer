"""Aggregated, user-specific dashboard metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import AnalysisResult, JobDescription, Resume, User
from app.schemas import AnalysisSummary, DashboardRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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


@router.get("", response_model=DashboardRead)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardRead:
    total_resumes = db.scalar(
        select(func.count()).select_from(Resume).where(Resume.owner_id == current_user.id)
    ) or 0
    total_jobs = db.scalar(
        select(func.count())
        .select_from(JobDescription)
        .where(JobDescription.owner_id == current_user.id)
    ) or 0
    total_analyses = db.scalar(
        select(func.count())
        .select_from(AnalysisResult)
        .where(AnalysisResult.owner_id == current_user.id)
    ) or 0
    average_score = db.scalar(
        select(func.avg(AnalysisResult.overall_score)).where(
            AnalysisResult.owner_id == current_user.id
        )
    )
    records = db.scalars(
        select(AnalysisResult)
        .where(AnalysisResult.owner_id == current_user.id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(10)
    ).all()
    best = db.scalar(
        select(AnalysisResult)
        .where(AnalysisResult.owner_id == current_user.id)
        .order_by(AnalysisResult.overall_score.desc())
        .limit(1)
    )
    return DashboardRead(
        total_resumes=int(total_resumes),
        total_jobs=int(total_jobs),
        total_analyses=int(total_analyses),
        average_score=round(float(average_score), 1) if average_score is not None else None,
        best_match=_summary(best) if best else None,
        recent_analyses=[_summary(record) for record in records[:5]],
        score_history=[
            {
                "date": record.created_at.date().isoformat(),
                "score": record.overall_score,
                "job_title": record.job_description.title,
            }
            for record in reversed(records)
        ],
    )