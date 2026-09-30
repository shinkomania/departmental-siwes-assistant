"""add canonical academic directory identity

Revision ID: 5f733fe82e7c
Revises: 0f5b0cfdfb95
Create Date: 2026-09-30 20:19:57.371633

"""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5f733fe82e7c"
down_revision = "0f5b0cfdfb95"
branch_labels = None
depends_on = None


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_identity(value):
    """
    Frozen E1.2 canonical identity normalization.

    Keep this implementation local to the migration so historical migration
    behavior cannot change if the application normalization code evolves.
    """
    if value is None:
        return None

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = _WHITESPACE_RE.sub(" ", normalized.strip())

    if not normalized:
        return None

    return normalized.casefold()


def _normalize_optional_identity(value):
    return _normalize_identity(value) or ""


def _load_legacy_directory_rows(connection):
    """
    Read the complete E1.1 academic-directory identity surface before any
    E1.2 schema mutation occurs.

    Only columns that exist at E1.1 are referenced here.
    """
    institutions = sa.table(
        "institutions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )

    academic_units = sa.table(
        "academic_units",
        sa.column("id", sa.Integer),
        sa.column("institution_id", sa.Integer),
        sa.column("name", sa.String),
    )

    departments = sa.table(
        "departments",
        sa.column("id", sa.Integer),
        sa.column("academic_unit_id", sa.Integer),
        sa.column("name", sa.String),
    )

    programmes = sa.table(
        "programmes",
        sa.column("id", sa.Integer),
        sa.column("department_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("award", sa.String),
    )

    return {
        "institutions": connection.execute(
            sa.select(
                institutions.c.id,
                institutions.c.name,
            )
        ).all(),
        "academic_units": connection.execute(
            sa.select(
                academic_units.c.id,
                academic_units.c.institution_id,
                academic_units.c.name,
            )
        ).all(),
        "departments": connection.execute(
            sa.select(
                departments.c.id,
                departments.c.academic_unit_id,
                departments.c.name,
            )
        ).all(),
        "programmes": connection.execute(
            sa.select(
                programmes.c.id,
                programmes.c.department_id,
                programmes.c.name,
                programmes.c.award,
            )
        ).all(),
    }


def _assert_non_empty_identity(
    entity_name,
    row_id,
    normalized_name,
):
    if normalized_name is None:
        raise RuntimeError(
            "Cannot migrate academic directory: "
            f"{entity_name} id={row_id} has an empty canonical name."
        )


def _assert_unique_identity(
    seen,
    identity,
    entity_name,
):
    if identity in seen:
        raise RuntimeError(
            "Cannot migrate academic directory: "
            f"{entity_name} canonical identity collision detected. "
            "Resolve duplicate legacy records before retrying migration."
        )

    seen.add(identity)


def _preflight_legacy_directory(connection):
    """
    Validate the E1.1 academic directory entirely before E1.2 performs DDL.

    This is intentionally a read-only operation. SQLite migration failure
    must not leave canonical columns behind while Alembic remains at E1.1.
    """
    rows = _load_legacy_directory_rows(connection)

    institution_identities = set()

    for row in rows["institutions"]:
        normalized_name = _normalize_identity(row.name)

        _assert_non_empty_identity(
            "Institution",
            row.id,
            normalized_name,
        )

        _assert_unique_identity(
            institution_identities,
            normalized_name,
            "Institution",
        )

    academic_unit_identities = set()

    for row in rows["academic_units"]:
        normalized_name = _normalize_identity(row.name)

        _assert_non_empty_identity(
            "AcademicUnit",
            row.id,
            normalized_name,
        )

        _assert_unique_identity(
            academic_unit_identities,
            (
                row.institution_id,
                normalized_name,
            ),
            "AcademicUnit",
        )

    department_identities = set()

    for row in rows["departments"]:
        normalized_name = _normalize_identity(row.name)

        _assert_non_empty_identity(
            "Department",
            row.id,
            normalized_name,
        )

        _assert_unique_identity(
            department_identities,
            (
                row.academic_unit_id,
                normalized_name,
            ),
            "Department",
        )

    programme_identities = set()

    for row in rows["programmes"]:
        normalized_name = _normalize_identity(row.name)

        _assert_non_empty_identity(
            "Programme",
            row.id,
            normalized_name,
        )

        normalized_award = _normalize_optional_identity(
            row.award
        )

        _assert_unique_identity(
            programme_identities,
            (
                row.department_id,
                normalized_name,
                normalized_award,
            ),
            "Programme",
        )


def _backfill_identity_columns(connection):
    institutions = sa.table(
        "institutions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("normalized_name", sa.String),
    )

    academic_units = sa.table(
        "academic_units",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("normalized_name", sa.String),
    )

    departments = sa.table(
        "departments",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("normalized_name", sa.String),
    )

    programmes = sa.table(
        "programmes",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("award", sa.String),
        sa.column("normalized_name", sa.String),
        sa.column("normalized_award", sa.String),
    )

    for row in connection.execute(
        sa.select(institutions.c.id, institutions.c.name)
    ):
        normalized_name = _normalize_identity(row.name)

        if normalized_name is None:
            raise RuntimeError(
                "Cannot migrate academic directory: Institution "
                f"id={row.id} has an empty canonical name."
            )

        connection.execute(
            institutions.update()
            .where(institutions.c.id == row.id)
            .values(normalized_name=normalized_name)
        )

    for row in connection.execute(
        sa.select(academic_units.c.id, academic_units.c.name)
    ):
        normalized_name = _normalize_identity(row.name)

        if normalized_name is None:
            raise RuntimeError(
                "Cannot migrate academic directory: AcademicUnit "
                f"id={row.id} has an empty canonical name."
            )

        connection.execute(
            academic_units.update()
            .where(academic_units.c.id == row.id)
            .values(normalized_name=normalized_name)
        )

    for row in connection.execute(
        sa.select(departments.c.id, departments.c.name)
    ):
        normalized_name = _normalize_identity(row.name)

        if normalized_name is None:
            raise RuntimeError(
                "Cannot migrate academic directory: Department "
                f"id={row.id} has an empty canonical name."
            )

        connection.execute(
            departments.update()
            .where(departments.c.id == row.id)
            .values(normalized_name=normalized_name)
        )

    for row in connection.execute(
        sa.select(
            programmes.c.id,
            programmes.c.name,
            programmes.c.award,
        )
    ):
        normalized_name = _normalize_identity(row.name)

        if normalized_name is None:
            raise RuntimeError(
                "Cannot migrate academic directory: Programme "
                f"id={row.id} has an empty canonical name."
            )

        connection.execute(
            programmes.update()
            .where(programmes.c.id == row.id)
            .values(
                normalized_name=normalized_name,
                normalized_award=_normalize_optional_identity(
                    row.award
                ),
            )
        )


def upgrade():
    connection = op.get_bind()

    # Phase 0: read-only validation of the complete legacy identity surface.
    # No E1.2 DDL may occur before this succeeds.
    _preflight_legacy_directory(connection)

    # Phase 1: expand the schema with nullable canonical columns so existing
    # legacy rows can be backfilled safely.
    with op.batch_alter_table(
        "institutions",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "normalized_name",
                sa.String(length=200),
                nullable=True,
            )
        )

    with op.batch_alter_table(
        "academic_units",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "normalized_name",
                sa.String(length=200),
                nullable=True,
            )
        )

    with op.batch_alter_table(
        "departments",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "normalized_name",
                sa.String(length=200),
                nullable=True,
            )
        )

    with op.batch_alter_table(
        "programmes",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "normalized_name",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "normalized_award",
                sa.String(length=100),
                nullable=True,
            )
        )

    # Phase 2: deterministically backfill the new canonical columns.
    _backfill_identity_columns(connection)

    # Phase 3: enforce the canonical identity contract.
    with op.batch_alter_table(
        "institutions",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "normalized_name",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.create_index(
            "ix_institutions_normalized_name",
            ["normalized_name"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_institutions_normalized_name",
            ["normalized_name"],
        )

    with op.batch_alter_table(
        "academic_units",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "normalized_name",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.create_index(
            "ix_academic_units_normalized_name",
            ["normalized_name"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_academic_units_institution_normalized_name",
            ["institution_id", "normalized_name"],
        )

    with op.batch_alter_table(
        "departments",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "normalized_name",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.create_index(
            "ix_departments_normalized_name",
            ["normalized_name"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_departments_unit_normalized_name",
            ["academic_unit_id", "normalized_name"],
        )

    with op.batch_alter_table(
        "programmes",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "normalized_name",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.alter_column(
            "normalized_award",
            existing_type=sa.String(length=100),
            nullable=False,
        )
        batch_op.create_index(
            "ix_programmes_normalized_name",
            ["normalized_name"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_programmes_department_normalized_identity",
            [
                "department_id",
                "normalized_name",
                "normalized_award",
            ],
        )


def downgrade():
    with op.batch_alter_table(
        "programmes",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_programmes_department_normalized_identity",
            type_="unique",
        )
        batch_op.drop_index(
            "ix_programmes_normalized_name"
        )
        batch_op.drop_column("normalized_award")
        batch_op.drop_column("normalized_name")

    with op.batch_alter_table(
        "departments",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_departments_unit_normalized_name",
            type_="unique",
        )
        batch_op.drop_index(
            "ix_departments_normalized_name"
        )
        batch_op.drop_column("normalized_name")

    with op.batch_alter_table(
        "academic_units",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_academic_units_institution_normalized_name",
            type_="unique",
        )
        batch_op.drop_index(
            "ix_academic_units_normalized_name"
        )
        batch_op.drop_column("normalized_name")

    with op.batch_alter_table(
        "institutions",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_institutions_normalized_name",
            type_="unique",
        )
        batch_op.drop_index(
            "ix_institutions_normalized_name"
        )
        batch_op.drop_column("normalized_name")
