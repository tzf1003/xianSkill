"""add ai providers and project ai binding

Revision ID: 0016_ai_providers
Revises: 0015_xgj_reward_modes
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_ai_providers"
down_revision = "0015_xgj_reward_modes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("protocol", sa.Enum("openai", "anthropic", "gemini", "volcengine", name="ai_protocol", native_enum=False), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("models", sa.JSON(), nullable=True, comment="已保存的模型列表"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("projects", sa.Column("ai_provider_id", sa.UUID(), nullable=True, comment="项目使用的 AI 服务商"))
    op.add_column("projects", sa.Column("ai_model", sa.String(length=200), nullable=True, comment="项目使用的模型 ID"))
    op.create_index("ix_projects_ai_provider_id", "projects", ["ai_provider_id"])
    op.create_foreign_key(
        "fk_projects_ai_provider_id",
        "projects",
        "ai_providers",
        ["ai_provider_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_ai_provider_id", "projects", type_="foreignkey")
    op.drop_index("ix_projects_ai_provider_id", table_name="projects")
    op.drop_column("projects", "ai_model")
    op.drop_column("projects", "ai_provider_id")

    op.drop_table("ai_providers")
    sa.Enum(name="ai_protocol").drop(op.get_bind(), checkfirst=False)