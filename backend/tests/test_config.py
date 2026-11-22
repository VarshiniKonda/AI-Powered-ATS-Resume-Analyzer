import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db import create_database_engine, normalize_database_url

PRODUCTION_DATABASE_URL = (
    "postgresql://user:password@db.example.supabase.co:5432/postgres?sslmode=require"
)


def test_supabase_postgresql_url_uses_psycopg_driver() -> None:
    assert normalize_database_url(
        "postgresql://postgres:example@db.example.supabase.co:5432/postgres?sslmode=require"
    ) == (
        "postgresql+psycopg://postgres:example@db.example.supabase.co:5432/postgres"
        "?sslmode=require"
    )
    assert normalize_database_url("postgres://user:pass@db.example/postgres") == (
        "postgresql+psycopg://user:pass@db.example/postgres"
    )


def test_supabase_engine_uses_psycopg_without_connecting() -> None:
    engine = create_database_engine(PRODUCTION_DATABASE_URL)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()


def test_production_settings_require_secret_and_https_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="short",
            database_url=PRODUCTION_DATABASE_URL,
            cors_origins="https://app.example.vercel.app",
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="s" * 40,
            database_url=PRODUCTION_DATABASE_URL,
            cors_origins="http://app.example.vercel.app",
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="s" * 40,
            database_url="postgresql://user:password@db.example.supabase.co/postgres",
            cors_origins="https://app.example.vercel.app",
        )


def test_production_settings_accept_vercel_origin() -> None:
    config = Settings(
        _env_file=None,
        environment="production",
        secret_key="s" * 40,
        database_url=PRODUCTION_DATABASE_URL,
        cors_origins="https://app.example.vercel.app/",
    )

    assert config.cors_origin_list == ["https://app.example.vercel.app"]
