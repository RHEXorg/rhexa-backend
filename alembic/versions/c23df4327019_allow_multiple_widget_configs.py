"""allow multiple widget configs

Revision ID: c23df4327019
Revises: 814295300a5a
Create Date: 2026-01-24 08:37:20.390609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c23df4327019'
down_revision: Union[str, Sequence[str], None] = '814295300a5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('widget_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(), nullable=True))
        # This will recreate the table without the unique constraint on organization_id
        # because we are NOT defining it in the batch session.
        batch_op.drop_constraint('widget_configs_organization_id_key', type_='unique')
        # Note: If it doesn't have a name, SQLAlchemy/Alembic tries to find it.
        # SQLite often needs naming convention or it might fail if unnamed.
        # However, simply running batch mode with drop_constraint is the correct way.

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('widget_configs', schema=None) as batch_op:
        batch_op.create_unique_constraint('widget_configs_organization_id_key', ['organization_id'])
        batch_op.drop_column('name')
