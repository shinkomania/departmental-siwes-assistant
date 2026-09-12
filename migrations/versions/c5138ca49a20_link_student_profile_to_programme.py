"""link student profile to programme

Revision ID: c5138ca49a20
Revises: 678ceb278713
Create Date: 2026-09-10 15:15:40.343749
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5138ca49a20'
down_revision = '678ceb278713'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('programme_id', sa.Integer(), nullable=True)
        )

        batch_op.create_foreign_key(
            'fk_student_profiles_programme_id_programmes',
            'programmes',
            ['programme_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_student_profiles_programme_id_programmes',
            type_='foreignkey'
        )

        batch_op.drop_column('programme_id')