"""add organization provenance fields

Revision ID: 025dbbc0c401
Revises: b897efb6d621
Create Date: 2026-09-12 08:51:03.951622

This migration intentionally avoids unrelated nullability changes on legacy
organization columns. New non-null provenance/status columns use safe database
defaults so existing organization rows can be migrated without failing.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '025dbbc0c401'
down_revision = 'b897efb6d621'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'source_type',
                sa.String(length=60),
                nullable=False,
                server_default='Other',
            )
        )
        batch_op.add_column(
            sa.Column('source_name', sa.String(length=180), nullable=True)
        )
        batch_op.add_column(
            sa.Column('source_url', sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column('source_reference', sa.String(length=180), nullable=True)
        )
        batch_op.add_column(
            sa.Column('source_last_checked', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('provenance_notes', sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'review_status',
                sa.String(length=30),
                nullable=False,
                server_default='Pending',
            )
        )
        batch_op.add_column(
            sa.Column('reviewed_at', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'listing_status',
                sa.String(length=20),
                nullable=False,
                server_default='Unknown',
            )
        )
        batch_op.add_column(
            sa.Column(
                'acceptance_status',
                sa.String(length=30),
                nullable=False,
                server_default='Unknown',
            )
        )
        batch_op.add_column(
            sa.Column(
                'acceptance_source_name',
                sa.String(length=180),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                'acceptance_source_url',
                sa.String(length=500),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column('acceptance_last_checked', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('acceptance_notes', sa.Text(), nullable=True)
        )

        batch_op.create_index(
            batch_op.f('ix_organizations_acceptance_status'),
            ['acceptance_status'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_organizations_industry'),
            ['industry'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_organizations_listing_status'),
            ['listing_status'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_organizations_review_status'),
            ['review_status'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_organizations_source_type'),
            ['source_type'],
            unique=False,
        )

    # Preserve the old source label as provenance metadata where possible.
    op.execute(
        """
        UPDATE organizations
        SET source_name = source
        WHERE source_name IS NULL
          AND source IS NOT NULL
          AND TRIM(source) <> ''
        """
    )


def downgrade():
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_organizations_source_type'))
        batch_op.drop_index(batch_op.f('ix_organizations_review_status'))
        batch_op.drop_index(batch_op.f('ix_organizations_listing_status'))
        batch_op.drop_index(batch_op.f('ix_organizations_industry'))
        batch_op.drop_index(batch_op.f('ix_organizations_acceptance_status'))

        batch_op.drop_column('acceptance_notes')
        batch_op.drop_column('acceptance_last_checked')
        batch_op.drop_column('acceptance_source_url')
        batch_op.drop_column('acceptance_source_name')
        batch_op.drop_column('acceptance_status')
        batch_op.drop_column('listing_status')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('review_status')
        batch_op.drop_column('provenance_notes')
        batch_op.drop_column('source_last_checked')
        batch_op.drop_column('source_reference')
        batch_op.drop_column('source_url')
        batch_op.drop_column('source_name')
        batch_op.drop_column('source_type')
