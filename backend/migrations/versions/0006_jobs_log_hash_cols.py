"""0006 — jobs 表补充 log_text / input_hash / output_hash 列

Revision ID: 0006_jobs_log_hash_cols
Revises: 0005_projects_skill_id
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_jobs_log_hash_cols"
down_revision: Union[str, None] = "0005_projects_skill_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("log_text", sa.Text, nullable=True))
    op.add_column("jobs", sa.Column("input_hash", sa.String(128), nullable=True))
    op.add_column("jobs", sa.Column("output_hash", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "output_hash")
    op.drop_column("jobs", "input_hash")
    op.drop_column("jobs", "log_text")
