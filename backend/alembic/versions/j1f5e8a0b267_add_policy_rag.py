"""add permission-aware policy RAG storage

Revision ID: j1f5e8a0b267
Revises: i0e4g7d9f156
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "j1f5e8a0b267"
down_revision: str | None = "i0e4g7d9f156"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PUBLISHED"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("access_scope", sa.String(length=24), nullable=False, server_default="ALL"),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("role_code", sa.String(length=60), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", "version", name="uq_policy_document_slug_version"),
    )
    op.create_index("ix_policy_documents_slug", "policy_documents", ["slug"])
    op.create_index("ix_policy_documents_status", "policy_documents", ["status"])
    op.create_index("ix_policy_documents_is_active", "policy_documents", ["is_active"])
    op.create_index("ix_policy_documents_access_scope", "policy_documents", ["access_scope"])
    op.create_index("ix_policy_documents_department_id", "policy_documents", ["department_id"])
    op.create_index("ix_policy_documents_role_code", "policy_documents", ["role_code"])
    op.create_index("ix_policy_documents_created_by", "policy_documents", ["created_by"])
    op.create_index(
        "ix_policy_documents_scope_status",
        "policy_documents",
        ["access_scope", "status", "is_active"],
    )

    if is_postgres:
        op.execute(
            """
            CREATE TABLE policy_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES policy_documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                page INTEGER NULL,
                section VARCHAR(220) NULL,
                embedding vector(64) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                CONSTRAINT uq_policy_chunk_position UNIQUE (document_id, chunk_index)
            )
            """
        )
    else:
        op.create_table(
            "policy_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("page", sa.Integer(), nullable=True),
            sa.Column("section", sa.String(length=220), nullable=True),
            sa.Column("embedding", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("document_id", "chunk_index", name="uq_policy_chunk_position"),
        )
    op.create_index("ix_policy_chunks_document_id", "policy_chunks", ["document_id"])
    op.create_index("ix_policy_chunks_document", "policy_chunks", ["document_id", "chunk_index"])


def downgrade() -> None:
    op.drop_index("ix_policy_chunks_document", table_name="policy_chunks")
    op.drop_index("ix_policy_chunks_document_id", table_name="policy_chunks")
    op.drop_table("policy_chunks")
    op.drop_index("ix_policy_documents_scope_status", table_name="policy_documents")
    op.drop_index("ix_policy_documents_created_by", table_name="policy_documents")
    op.drop_index("ix_policy_documents_role_code", table_name="policy_documents")
    op.drop_index("ix_policy_documents_department_id", table_name="policy_documents")
    op.drop_index("ix_policy_documents_access_scope", table_name="policy_documents")
    op.drop_index("ix_policy_documents_is_active", table_name="policy_documents")
    op.drop_index("ix_policy_documents_status", table_name="policy_documents")
    op.drop_index("ix_policy_documents_slug", table_name="policy_documents")
    op.drop_table("policy_documents")
    # Do not DROP EXTENSION vector: the database may have other vector users.
