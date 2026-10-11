"""Remove the unapproved drone-model BOM feature."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_remove_bom_feature"
down_revision: str | None = "0004_catalog_bom"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "drone_model_bom_items" in tables:
        op.drop_table("drone_model_bom_items")
    if "drone_model_boms" in tables:
        op.drop_table("drone_model_boms")


def downgrade() -> None:
    # The removed BOM feature is intentionally not restored by downgrade.
    pass
