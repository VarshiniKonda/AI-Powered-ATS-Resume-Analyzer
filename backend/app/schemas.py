"""Validated API request and response schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("full_name")
    @classmethod
    def strip_updated_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserRead


class ResumeRead(BaseModel):
    id: int
    filename: str
    parsed_data: dict[str, Any]
    created_at: datetime


class JobCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    content_text: str = Field(min_length=30, max_length=50_000)
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_skills: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("content_text")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 30:
            raise ValueError("Job description must contain at least 30 characters.")
        return value


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    content_text: str | None = Field(default=None, min_length=30, max_length=50_000)
    required_skills: list[str] | None = Field(default=None, max_length=100)
    preferred_skills: list[str] | None = Field(default=None, max_length=100)


class JobRead(BaseModel):
    id: int
    title: str
    company: str | None
    content_text: str
    parsed_data: dict[str, Any]
    created_at: datetime


class AnalysisCreate(BaseModel):
    resume_id: int
    job_description_id: int


class AnalysisSummary(BaseModel):
    id: int
    resume_id: int
    resume_filename: str
    job_description_id: int
    job_title: str
    company: str | None
    overall_score: float
    created_at: datetime


class AnalysisRead(AnalysisSummary):
    breakdown: dict[str, Any]
    details: dict[str, Any]


class ApplicationCreate(BaseModel):
    job_description_id: int
    status: Literal["Applied", "In Progress", "Interview", "Rejected", "Selected"] = "In Progress"
    notes: str | None = Field(default=None, max_length=4000)


class ApplicationUpdate(BaseModel):
    status: Literal["Applied", "In Progress", "Interview", "Rejected", "Selected"] | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ApplicationRead(BaseModel):
    id: int
    job_description_id: int
    job_title: str
    company: str | None
    status: str
    notes: str | None
    updated_at: datetime
    latest_score: float | None = None


class DashboardRead(BaseModel):
    total_resumes: int
    total_jobs: int
    total_analyses: int
    average_score: float | None
    best_match: AnalysisSummary | None
    recent_analyses: list[AnalysisSummary]
    score_history: list[dict[str, Any]]