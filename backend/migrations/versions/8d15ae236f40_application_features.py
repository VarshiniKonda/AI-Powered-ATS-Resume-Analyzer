"""Add user display names, parsed data and skill findings.

Revision ID: 8d15ae236f40
Revises: 4ac93f7bb894
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8d15ae236f40"
down_revision: Union[str, None] = "4ac93f7bb894"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(length=120), nullable=False, server_default=""),
    )
    op.add_column(
        "resumes",
        sa.Column("parsed_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("parsed_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "matched_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("skill", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("match_type", sa.String(length=20), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_matched_skills_analysis_id"),
        "matched_skills",
        ["analysis_id"],
        unique=False,
    )
    op.create_table(
        "missing_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("skill", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_missing_skills_analysis_id"),
        "missing_skills",
        ["analysis_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_missing_skills_analysis_id"), table_name="missing_skills")
    op.drop_table("missing_skills")
    op.drop_index(op.f("ix_matched_skills_analysis_id"), table_name="matched_skills")
    op.drop_table("matched_skills")
    op.drop_column("job_descriptions", "parsed_json")
    op.drop_column("resumes", "parsed_json")
    op.drop_column("users", "full_name")
