"""Add the single-company shared mailbox connection record."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_shared_mailbox"
down_revision: str | None = "0009_expand_inventory_location"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)
    op.create_table(
        "mailbox_connections",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="google_gmail"),
        sa.Column("mailbox_email", sa.String(320), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_connected"),
        sa.Column("refresh_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=True),
        sa.Column("connected_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", now, nullable=False),
        sa.Column("updated_at", now, nullable=False),
        sa.UniqueConstraint("company_id", name="uq_mailbox_connection_company"),
    )
    op.create_index("ix_mailbox_connections_company_id", "mailbox_connections", ["company_id"])


def downgrade() -> None:
    op.drop_table("mailbox_connections")
