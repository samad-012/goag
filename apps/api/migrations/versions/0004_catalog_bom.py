"""Add GOAG catalog metadata and versioned drone-model BOMs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_catalog_bom"
down_revision: str | None = "0003_drone_checklist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    component_columns = {column["name"] for column in inspector.get_columns("component_catalog")}

    if "minimum_stock" not in component_columns:
        op.add_column("component_catalog", sa.Column("minimum_stock", sa.Integer(), nullable=False, server_default="0"))
    if "storage_location" not in component_columns:
        op.add_column("component_catalog", sa.Column("storage_location", sa.String(200), nullable=False, server_default=""))
    if "remarks" not in component_columns:
        op.add_column("component_catalog", sa.Column("remarks", sa.Text(), nullable=False, server_default=""))

    if "drone_models" not in table_names:
        op.create_table(
            "drone_models",
            sa.Column("id", uuid, primary_key=True),
            sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("code", sa.String(100), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("created_at", now, nullable=False),
            sa.UniqueConstraint("company_id", "code", name="uq_drone_model_company_code"),
        )
    else:
        model_columns = {column["name"] for column in inspector.get_columns("drone_models")}
        if "company_id" not in model_columns:
            op.add_column("drone_models", sa.Column("company_id", uuid, nullable=True))
        if "code" not in model_columns:
            op.add_column("drone_models", sa.Column("code", sa.String(100), nullable=True))
        if "status" not in model_columns:
            op.add_column("drone_models", sa.Column("status", sa.String(32), nullable=False, server_default="active"))
        bind.execute(sa.text("UPDATE public.drone_models SET company_id = (SELECT id FROM public.companies ORDER BY created_at LIMIT 1) WHERE company_id IS NULL"))
        bind.execute(sa.text("UPDATE public.drone_models SET code = regexp_replace(upper(trim(name)), '[^A-Z0-9]+', '-', 'g') WHERE code IS NULL"))
        op.alter_column("drone_models", "company_id", nullable=False)
        op.alter_column("drone_models", "code", nullable=False)
        if not any("company_id" in fk.get("constrained_columns", []) for fk in inspector.get_foreign_keys("drone_models")):
            op.create_foreign_key("fk_drone_models_company_id", "drone_models", "companies", ["company_id"], ["id"])

    refreshed = sa.inspect(bind)
    if "ix_drone_models_company_id" not in {index["name"] for index in refreshed.get_indexes("drone_models") if index.get("name")}:
        op.create_index("ix_drone_models_company_id", "drone_models", ["company_id"])
    if "uq_drone_model_company_code" not in {constraint["name"] for constraint in refreshed.get_unique_constraints("drone_models") if constraint.get("name")}:
        op.create_unique_constraint("uq_drone_model_company_code", "drone_models", ["company_id", "code"])

    op.create_table(
        "drone_model_boms",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("drone_model_id", uuid, sa.ForeignKey("drone_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", now, nullable=False),
        sa.UniqueConstraint("drone_model_id", "version", name="uq_drone_model_bom_version"),
    )
    op.create_index("ix_drone_model_boms_company_id", "drone_model_boms", ["company_id"])
    op.create_index("ix_drone_model_boms_drone_model_id", "drone_model_boms", ["drone_model_id"])

    op.create_table(
        "drone_model_bom_items",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("bom_id", uuid, sa.ForeignKey("drone_model_boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", uuid, sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("required_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("bom_id", "component_id", name="uq_drone_model_bom_component"),
        sa.CheckConstraint("required_quantity > 0", name="ck_drone_model_bom_item_quantity_positive"),
    )
    op.create_index("ix_drone_model_bom_items_bom_id", "drone_model_bom_items", ["bom_id"])
    op.create_index("ix_drone_model_bom_items_component_id", "drone_model_bom_items", ["component_id"])

    op.add_column("drones", sa.Column("drone_model_id", uuid, sa.ForeignKey("drone_models.id"), nullable=True))
    op.create_index("ix_drones_drone_model_id", "drones", ["drone_model_id"])


def downgrade() -> None:
    op.drop_index("ix_drones_drone_model_id", table_name="drones")
    op.drop_column("drones", "drone_model_id")
    op.drop_table("drone_model_bom_items")
    op.drop_table("drone_model_boms")
    # Keep drone_models because this migration can upgrade the MVP table in place.
    # Dropping it here would destroy pre-existing model records during a rollback.
    op.drop_column("component_catalog", "remarks")
    op.drop_column("component_catalog", "storage_location")
    op.drop_column("component_catalog", "minimum_stock")
