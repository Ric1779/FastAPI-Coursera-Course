"""add shipment created_at

Revision ID: 404ae6c42747
Revises: 5b0091e92ef3
Create Date: 2026-10-02 11:54:14.948028

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "404ae6c42747"
down_revision: str | Sequence[str] | None = "5b0091e92ef3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("shipment", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.execute(
        """
        UPDATE shipment AS s
        SET created_at = e.started_at
        FROM (
            SELECT shipment_id, MIN(created_at) AS started_at
            FROM shipment_event
            GROUP BY shipment_id
        ) AS e
        WHERE s.id = e.shipment_id
        """
    )
    op.execute("UPDATE shipment SET created_at = NOW() WHERE created_at IS NULL")
    op.alter_column("shipment", "created_at", nullable=False)


def downgrade() -> None:
    op.drop_column("shipment", "created_at")
