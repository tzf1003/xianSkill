"""0003 — 新增 projects 表，skills 表添加 project_id 外键

Revision ID: 0003_projects
Revises: 0002_m3_human_delivery
Create Date: 2026-03-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_projects"
down_revision: Union[str, None] = "0002_m3_human_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- projects --
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("type", sa.String(50), server_default="photo_restore", nullable=False),
        sa.Column("options", postgresql.JSONB, nullable=True),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_projects_slug"),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])

    # -- skills: 新增 project_id 外键 --
    op.add_column(
        "skills",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_skills_project_id", "skills", ["project_id"])

    # -- skills: 新增 prompt_template / runner_config（迁移补充，首次部署已包含） --
    # 仅在列不存在时执行，使用 try/except 跳过
    try:
        op.add_column("skills", sa.Column("prompt_template", sa.Text, nullable=True))
    except Exception:
        pass
    try:
        op.add_column("skills", sa.Column("runner_config", postgresql.JSONB, nullable=True))
    except Exception:
        pass


def downgrade() -> None:
    op.drop_index("ix_skills_project_id", table_name="skills")
    op.drop_column("skills", "project_id")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")
