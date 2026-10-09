"""initial

Revision ID: d7b220f72fba
Revises:
Create Date: 2026-10-09 13:45:30.758900

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d7b220f72fba"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
