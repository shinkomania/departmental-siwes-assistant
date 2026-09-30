"""
Academic Directory Alternative and Source Identities
-----------------------------------------------------

Provides controlled identity mappings around DSA's authoritative academic
directory.

AcademicDirectoryAlias records an explicitly accepted alternative textual
identity for exactly one authoritative academic entity.

AcademicDirectorySourceIdentity records how one registered DataSource
identifies exactly one authoritative academic entity.

These records do not publish, verify, activate, merge or SIWES-enable an
academic entity. They provide identity infrastructure for later controlled
source-import and review workflows.
"""

from datetime import datetime

from sqlalchemy import event

from domain.academic_identity import (
    normalize_directory_identity,
    normalize_optional_directory_identity,
)

from .db import db


class AcademicDirectoryAlias(db.Model):
    __tablename__ = "academic_directory_aliases"

    id = db.Column(db.Integer, primary_key=True)

    alias = db.Column(
        db.String(300),
        nullable=False,
    )

    normalized_alias = db.Column(
        db.String(300),
        nullable=False,
        index=True,
    )

    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id"),
        nullable=True,
        index=True,
    )

    academic_unit_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_units.id"),
        nullable=True,
        index=True,
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=True,
        index=True,
    )

    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id"),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    institution = db.relationship(
        "Institution",
        foreign_keys=[institution_id],
    )

    academic_unit = db.relationship(
        "AcademicUnit",
        foreign_keys=[academic_unit_id],
    )

    department = db.relationship(
        "Department",
        foreign_keys=[department_id],
    )

    programme = db.relationship(
        "Programme",
        foreign_keys=[programme_id],
    )

    __table_args__ = (
        db.CheckConstraint(
            """
            (
                CASE WHEN institution_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN academic_unit_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN department_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN programme_id IS NOT NULL THEN 1 ELSE 0 END
            ) = 1
            """,
            name="ck_academic_directory_alias_exactly_one_target",
        ),
        db.UniqueConstraint(
            "institution_id",
            "normalized_alias",
            name="uq_academic_directory_alias_institution",
        ),
        db.UniqueConstraint(
            "academic_unit_id",
            "normalized_alias",
            name="uq_academic_directory_alias_academic_unit",
        ),
        db.UniqueConstraint(
            "department_id",
            "normalized_alias",
            name="uq_academic_directory_alias_department",
        ),
        db.UniqueConstraint(
            "programme_id",
            "normalized_alias",
            name="uq_academic_directory_alias_programme",
        ),
    )

    @property
    def target_type(self):
        if self.institution_id is not None:
            return "Institution"
        if self.academic_unit_id is not None:
            return "AcademicUnit"
        if self.department_id is not None:
            return "Department"
        if self.programme_id is not None:
            return "Programme"
        return None

    @property
    def target_id(self):
        for value in (
            self.institution_id,
            self.academic_unit_id,
            self.department_id,
            self.programme_id,
        ):
            if value is not None:
                return value
        return None

    def __repr__(self):
        return (
            f"<AcademicDirectoryAlias "
            f"{self.normalized_alias!r} "
            f"{self.target_type}:{self.target_id}>"
        )


class AcademicDirectorySourceIdentity(db.Model):
    __tablename__ = "academic_directory_source_identities"

    id = db.Column(db.Integer, primary_key=True)

    data_source_id = db.Column(
        db.Integer,
        db.ForeignKey("data_sources.id"),
        nullable=False,
        index=True,
    )

    external_identifier = db.Column(
        db.String(300),
        nullable=True,
    )

    external_name = db.Column(
        db.String(300),
        nullable=True,
    )

    normalized_external_name = db.Column(
        db.String(300),
        nullable=False,
        default="",
        index=True,
    )

    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id"),
        nullable=True,
        index=True,
    )

    academic_unit_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_units.id"),
        nullable=True,
        index=True,
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=True,
        index=True,
    )

    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id"),
        nullable=True,
        index=True,
    )

    reference_url = db.Column(
        db.String(1000),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    data_source = db.relationship(
        "DataSource",
        backref=db.backref(
            "academic_directory_source_identities",
            lazy=True,
        ),
    )

    institution = db.relationship(
        "Institution",
        foreign_keys=[institution_id],
    )

    academic_unit = db.relationship(
        "AcademicUnit",
        foreign_keys=[academic_unit_id],
    )

    department = db.relationship(
        "Department",
        foreign_keys=[department_id],
    )

    programme = db.relationship(
        "Programme",
        foreign_keys=[programme_id],
    )

    __table_args__ = (
        db.CheckConstraint(
            """
            (
                CASE WHEN institution_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN academic_unit_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN department_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN programme_id IS NOT NULL THEN 1 ELSE 0 END
            ) = 1
            """,
            name=(
                "ck_academic_directory_source_identity_"
                "exactly_one_target"
            ),
        ),
        db.CheckConstraint(
            """
            external_identifier IS NOT NULL
            OR external_name IS NOT NULL
            """,
            name=(
                "ck_academic_directory_source_identity_"
                "has_external_identity"
            ),
        ),
        db.Index(
            "uq_academic_directory_source_identity_source_identifier",
            "data_source_id",
            "external_identifier",
            unique=True,
            sqlite_where=db.text(
                "external_identifier IS NOT NULL"
            ),
        ),
        db.Index(
            "uq_academic_directory_source_identity_source_institution_name",
            "data_source_id",
            "institution_id",
            "normalized_external_name",
            unique=True,
            sqlite_where=db.text(
                "institution_id IS NOT NULL "
                "AND normalized_external_name <> ''"
            ),
        ),
        db.Index(
            "uq_academic_directory_source_identity_source_unit_name",
            "data_source_id",
            "academic_unit_id",
            "normalized_external_name",
            unique=True,
            sqlite_where=db.text(
                "academic_unit_id IS NOT NULL "
                "AND normalized_external_name <> ''"
            ),
        ),
        db.Index(
            "uq_academic_directory_source_identity_source_department_name",
            "data_source_id",
            "department_id",
            "normalized_external_name",
            unique=True,
            sqlite_where=db.text(
                "department_id IS NOT NULL "
                "AND normalized_external_name <> ''"
            ),
        ),
        db.Index(
            "uq_academic_directory_source_identity_source_programme_name",
            "data_source_id",
            "programme_id",
            "normalized_external_name",
            unique=True,
            sqlite_where=db.text(
                "programme_id IS NOT NULL "
                "AND normalized_external_name <> ''"
            ),
        ),
    )

    @property
    def target_type(self):
        if self.institution_id is not None:
            return "Institution"
        if self.academic_unit_id is not None:
            return "AcademicUnit"
        if self.department_id is not None:
            return "Department"
        if self.programme_id is not None:
            return "Programme"
        return None

    @property
    def target_id(self):
        for value in (
            self.institution_id,
            self.academic_unit_id,
            self.department_id,
            self.programme_id,
        ):
            if value is not None:
                return value
        return None

    def __repr__(self):
        return (
            f"<AcademicDirectorySourceIdentity "
            f"source={self.data_source_id} "
            f"{self.target_type}:{self.target_id}>"
        )


def _sync_academic_directory_alias(
    mapper,
    connection,
    target,
):
    target.normalized_alias = normalize_directory_identity(
        target.alias
    )


def _sync_academic_directory_source_identity(
    mapper,
    connection,
    target,
):
    target.normalized_external_name = (
        normalize_optional_directory_identity(
            target.external_name
        )
    )


event.listen(
    AcademicDirectoryAlias,
    "before_insert",
    _sync_academic_directory_alias,
)

event.listen(
    AcademicDirectoryAlias,
    "before_update",
    _sync_academic_directory_alias,
)

event.listen(
    AcademicDirectorySourceIdentity,
    "before_insert",
    _sync_academic_directory_source_identity,
)

event.listen(
    AcademicDirectorySourceIdentity,
    "before_update",
    _sync_academic_directory_source_identity,
)
