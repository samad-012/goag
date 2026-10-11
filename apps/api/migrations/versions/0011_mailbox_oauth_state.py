"""Add one-time state storage for the shared mailbox OAuth flow."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_mailbox_oauth_state"
down_revision: str | None = "0010_shared_mailbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("mailbox_connections", sa.Column("oauth_state_hash", sa.String(128), nullable=True))
    op.add_column(
        "mailbox_connections",
        sa.Column("oauth_state_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_mailbox_connections_oauth_state_hash",
        "mailbox_connections",
        ["oauth_state_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_mailbox_connections_oauth_state_hash", table_name="mailbox_connections")
    op.drop_column("mailbox_connections", "oauth_state_expires_at")
    op.drop_column("mailbox_connections", "oauth_state_hash")
