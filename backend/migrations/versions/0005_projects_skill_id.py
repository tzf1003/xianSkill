"""0005 — projects 表新增 skill_id 外键

Revision ID: 0005_projects_skill_id
Revises: 0004_sku_project_id
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_projects_skill_id"
down_revision: Union[str, None] = "0004_sku_project_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="SET NULL"),
            nullable=True,
            comment="该项目绑定的默认 Skill",
        ),
    )
    op.create_index("ix_projects_skill_id", "projects", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_projects_skill_id", table_name="projects")
    op.drop_column("projects", "skill_id")
