"""link student profile to user

Revision ID: 678ceb278713
Revises: 87f52b7e8e08
Create Date: 2026-09-02 22:14:12.517219
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '678ceb278713'
down_revision = '87f52b7e8e08'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('user_id', sa.Integer(), nullable=True)
        )

        batch_op.create_unique_constraint(
            'uq_student_profiles_user_id',
            ['user_id']
        )

        batch_op.create_foreign_key(
            'fk_student_profiles_user_id_users',
            'users',
            ['user_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_student_profiles_user_id_users',
            type_='foreignkey'
        )

        batch_op.drop_constraint(
            'uq_student_profiles_user_id',
            type_='unique'
        )

        batch_op.drop_column('user_id')