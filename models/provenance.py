"""
Trusted Data Source and Provenance Models
-----------------------------------------
Provides reusable source metadata and source-backed evidence for DSA.

A DataSource identifies where information came from.

A SourceEvidence record describes a specific claim supported by that source
against exactly one authoritative DSA entity.

Source authority and evidence do not themselves publish, verify, activate or
SIWES-enable an authoritative record. Those remain separate controlled
workflows.
"""

from datetime import datetime

from .db import db


class DataSource(db.Model):
    __tablename__ = "data_sources"

    SOURCE_TYPES = (
        "Regulator",
        "Government/Public Registry",
        "Institution Official Source",
        "Organization Official Source",
        "ITF SIWES Source",
        "Other Official Source",
        "Community Contribution",
        "Other",
    )

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        nullable=False,
        unique=True,
    )

    source_type = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    authority_name = db.Column(db.String(200))

    base_url = db.Column(db.String(500))

    description = db.Column(db.Text)

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
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

    def __repr__(self):
        return f"<DataSource {self.name}>"


class SourceEvidence(db.Model):
    __tablename__ = "source_evidence"

    CLAIM_TYPES = (
        "Institution Recognition",
        "Programme Recognition",
        "Academic Structure",
        "SIWES Configuration",
        "Directory Attribute",
        "Other",
    )

    id = db.Column(db.Integer, primary_key=True)

    data_source_id = db.Column(
        db.Integer,
        db.ForeignKey("data_sources.id"),
        nullable=False,
        index=True,
    )

    claim_type = db.Column(
        db.String(100),
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

    siwes_configuration_id = db.Column(
        db.Integer,
        db.ForeignKey("siwes_configurations.id"),
        nullable=True,
        index=True,
    )

    reference_url = db.Column(db.String(1000))
    reference_text = db.Column(db.String(500))

    evidence_note = db.Column(db.Text)

    observed_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    checked_at = db.Column(db.DateTime)

    checked_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    data_source = db.relationship(
        "DataSource",
        backref=db.backref("evidence_records", lazy=True),
    )

    checked_by = db.relationship(
        "User",
        foreign_keys=[checked_by_user_id],
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

    siwes_configuration = db.relationship(
        "SIWESConfiguration",
        foreign_keys=[siwes_configuration_id],
    )

    __table_args__ = (
        db.CheckConstraint(
            """
            (
                CASE WHEN institution_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN academic_unit_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN department_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN programme_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN siwes_configuration_id IS NOT NULL THEN 1 ELSE 0 END
            ) = 1
            """,
            name="ck_source_evidence_exactly_one_target",
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
        if self.siwes_configuration_id is not None:
            return "SIWESConfiguration"
        return None

    @property
    def target_id(self):
        for value in (
            self.institution_id,
            self.academic_unit_id,
            self.department_id,
            self.programme_id,
            self.siwes_configuration_id,
        ):
            if value is not None:
                return value
        return None

    def __repr__(self):
        return (
            f"<SourceEvidence {self.claim_type} "
            f"{self.target_type}:{self.target_id}>"
        )
