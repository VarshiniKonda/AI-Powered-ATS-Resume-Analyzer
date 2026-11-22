"""Application configuration loaded from environment variables."""

import json
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SECRET = "development-only-secret-change-before-production-123"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class Settings(BaseSettings):
    """Validated runtime settings; secrets are supplied by the deployment platform."""

    app_name: str = "AI-Powered ATS Resume Analyzer"
    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./ats_tracker.db"
    secret_key: str = DEVELOPMENT_SECRET
    cors_origins: str = "http://localhost:5173"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    max_upload_size_mb: int = Field(default=10, ge=1, le=50)
    semantic_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    scoring_weights: str = (
        '{"required_skills":35,"keyword_match":25,"experience":20,'
        '"education":40,"project_relevance":10}'
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized, explicitly configured browser origins."""
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def scoring_weight_map(self) -> dict[str, float]:
        weights = json.loads(self.scoring_weights)
        expected = {
            "required_skills",
            "keyword_match",
            "experience",
            "education",
            "project_relevance",
        }
        if (
            set(weights) != expected
            or any(not isinstance(value, (int, float)) or value < 0 for value in weights.values())
            or sum(weights.values()) <= 0
        ):
            raise ValueError("SCORING_WEIGHTS must define nonnegative weights for each score component.")
        return {key: float(value) for key, value in weights.items()}

    @model_validator(mode="after")
    def validate_deployment_settings(self) -> "Settings":
        self.scoring_weight_map
        if self.environment == "production":
            if self.secret_key == DEVELOPMENT_SECRET or len(self.secret_key) < 32:
                raise ValueError("Production requires a secret key of at least 32 characters.")
            if not self.cors_origin_list:
                raise ValueError("Production requires at least one allowed CORS origin.")
            database = urlsplit(self.database_url)
            ssl_modes = parse_qs(database.query).get("sslmode", [])
            if database.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
                raise ValueError("Production requires a PostgreSQL DATABASE_URL.")
            if not ssl_modes or ssl_modes[0] not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("Production PostgreSQL connections must require SSL.")

        for origin in self.cors_origin_list:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths.")
            if parsed.scheme != "https" and (
                self.environment == "production" or parsed.hostname not in LOCAL_HOSTS
            ):
                raise ValueError("Non-local CORS origins must use HTTPS.")

        return self


settings = Settings()