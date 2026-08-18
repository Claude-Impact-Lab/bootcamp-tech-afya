"""Baseline for the existing database state.

This revision ID already exists in the database's alembic_version table.
The original revision file was not present in the repository history, so this
local baseline records the known starting point without changing the schema.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "05a192260709"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
