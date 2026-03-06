"""0004 — SKU 添加 project_id，移除 skills.project_id

Skill 与 Project 完全解耦：同一个 Skill 可被多个 Project 的 SKU 引用。
Project 的选项配置通过 SKU.project_id 在运行时确定。

Revision ID: 0004_sku_project_id
Revises: 0003_projects
Create Date: 2026-03-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_sku_project_id"
down_revision: Union[str, None] = "0003_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # skus: 新增 project_id 外键
    op.add_column(
        "skus",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            comment="该 SKU 属于哪个项目（决定运行时加载哪个 Project 的选项配置）",
        ),
    )
    op.create_index("ix_skus_project_id", "skus", ["project_id"])

    # skills: 移除 project_id（Skill 与 Project 解耦，不再直接绑定）
    op.drop_index("ix_skills_project_id", table_name="skills")
    op.drop_column("skills", "project_id")


def downgrade() -> None:
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

    op.drop_index("ix_skus_project_id", table_name="skus")
    op.drop_column("skus", "project_id")
