"""Database models and relationships for user-owned application records."""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JSONText(TypeDecorator[dict[str, Any]]):
    """Keep JSON-shaped ORM values in the legacy migration's portable TEXT columns."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: dict[str, Any] | None, _dialect) -> str:
        return json.dumps(value or {}, ensure_ascii=False)

    def process_result_value(self, value: str | None, _dialect) -> dict[str, Any]:
        return json.loads(value) if value else {}


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    job_descriptions: Mapped[list["JobDescription"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    analyses: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    applications: Mapped[list["JobApplication"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSONText, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    owner: Mapped[User] = relationship(back_populates="resumes")
    analyses: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True
    )


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSONText, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    owner: Mapped[User] = relationship(back_populates="job_descriptions")
    analyses: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan", passive_deletes=True
    )
    application: Mapped["JobApplication | None"] = relationship(
        back_populates="job_description", cascade="all, delete-orphan", passive_deletes=True
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSONText, nullable=False, default=dict)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSONText, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    owner: Mapped[User] = relationship(back_populates="analyses")
    resume: Mapped[Resume] = relationship(back_populates="analyses")
    job_description: Mapped[JobDescription] = relationship(back_populates="analyses")
    matched_skills: Mapped[list["MatchedSkill"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    missing_skills: Mapped[list["MissingSkill"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class MatchedSkill(Base):
    __tablename__ = "matched_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")

    analysis: Mapped[AnalysisResult] = relationship(back_populates="matched_skills")


class MissingSkill(Base):
    __tablename__ = "missing_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    analysis: Mapped[AnalysisResult] = relationship(back_populates="missing_skills")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="In Progress")
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    owner: Mapped[User] = relationship(back_populates="applications")
    job_description: Mapped[JobDescription] = relationship(back_populates="application")