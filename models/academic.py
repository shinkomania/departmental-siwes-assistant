"""
Academic Structure and SIWES Configuration Models
--------------------------------------------------
Provides DSA's institution-neutral academic hierarchy:

Institution -> Academic Unit -> Department -> Programme -> SIWES Configuration

SIWES eligibility and timing are stored at programme level. DSA must not infer
SIWES participation solely from institution type, programme duration, or common
patterns such as 300 Level, 400 Level, ND, or NCE.
"""

from datetime import datetime
from .db import db


class Institution(db.Model):
    __tablename__ = "institutions"

    DIRECTORY_STATUSES = (
        "Pending Verification",
        "Verified",
        "Suspended",
        "Inactive",
        "Rejected",
    )

    ADMINISTRATION_STATUSES = (
        "Unclaimed",
        "Claimed",
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)

    # Examples: University, Polytechnic, College of Technology,
    # College of Agriculture, College of Education.
    institution_type = db.Column(db.String(100))

    state = db.Column(db.String(100))
    official_website = db.Column(db.String(255))

    directory_status = db.Column(
        db.String(50),
        default="Pending Verification",
    )
    administration_status = db.Column(
        db.String(50),
        default="Unclaimed",
    )

    verification_source = db.Column(db.Text)
    last_verified = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AcademicUnit(db.Model):
    __tablename__ = "academic_units"

    id = db.Column(db.Integer, primary_key=True)

    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id"),
        nullable=False,
    )

    name = db.Column(db.String(200), nullable=False)

    # Institution-neutral terminology. Examples:
    # Faculty, College, School, Directorate, Institute.
    unit_type = db.Column(
        db.String(50),
        nullable=False,
    )

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    institution = db.relationship(
        "Institution",
        backref=db.backref("academic_units", lazy=True),
    )


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)

    academic_unit_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_units.id"),
        nullable=False,
    )

    name = db.Column(db.String(200), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    academic_unit = db.relationship(
        "AcademicUnit",
        backref=db.backref("departments", lazy=True),
    )


class Programme(db.Model):
    __tablename__ = "programmes"

    id = db.Column(db.Integer, primary_key=True)

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False,
    )

    name = db.Column(db.String(200), nullable=False)

    # Examples: B.Eng., B.Sc., HND, ND, NCE.
    award = db.Column(db.String(100))

    # Normal academic duration of the programme where known.
    # This describes the programme; it does NOT determine SIWES eligibility.
    duration_years = db.Column(db.Integer)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship(
        "Department",
        backref=db.backref("programmes", lazy=True),
    )


class SIWESConfiguration(db.Model):
    __tablename__ = "siwes_configurations"

    SIWES_STATUSES = (
        "Required",
        "Optional",
        "No SIWES",
        "Pending Verification",
    )

    id = db.Column(db.Integer, primary_key=True)

    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id"),
        nullable=False,
        unique=True,
    )

    # Whether SIWES applies to this specific programme.
    siwes_status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending Verification",
    )

    # Duration of the SIWES attachment itself.
    duration_months = db.Column(db.Integer)

    # Flexible academic stage rather than a university-only level.
    # Examples:
    # "300 Level", "400 Level", "ND I", "After ND I", "Year 2".
    eligible_level = db.Column(db.String(100))

    # More precise timing where the level alone is insufficient.
    # Examples:
    # "After first semester", "End of ND I", "After second year".
    timing = db.Column(db.String(150))

    # Retained for compatibility and institution-specific semester rules.
    semester = db.Column(db.String(100))

    required_forms = db.Column(db.Text)
    special_requirements = db.Column(db.Text)

    # Evidence supporting this programme's SIWES configuration.
    verification_source = db.Column(db.Text)
    verification_reference = db.Column(db.String(255))
    last_verified = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    programme = db.relationship(
        "Programme",
        backref=db.backref(
            "siwes_configuration",
            uselist=False,
        ),
    )
