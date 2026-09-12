from datetime import datetime
from .db import db


class Institution(db.Model):
    __tablename__ = "institutions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    institution_type = db.Column(db.String(100))
    state = db.Column(db.String(100))
    official_website = db.Column(db.String(255))

    directory_status = db.Column(db.String(50), default="Pending Verification")
    administration_status = db.Column(db.String(50), default="Unclaimed")

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
        nullable=False
    )

    name = db.Column(db.String(200), nullable=False)

    unit_type = db.Column(
        db.String(50),
        nullable=False
    )

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    institution = db.relationship(
        "Institution",
        backref=db.backref("academic_units", lazy=True)
    )


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    academic_unit_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_units.id"),
        nullable=False
    )

    name = db.Column(db.String(200), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    academic_unit = db.relationship(
        "AcademicUnit",
        backref=db.backref("departments", lazy=True)
    )


class Programme(db.Model):
    __tablename__ = "programmes"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False
    )

    name = db.Column(db.String(200), nullable=False)
    award = db.Column(db.String(100))

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship(
        "Department",
        backref=db.backref("programmes", lazy=True)
    )


class SIWESConfiguration(db.Model):
    __tablename__ = "siwes_configurations"

    id = db.Column(db.Integer, primary_key=True)
    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id"),
        nullable=False,
        unique=True
    )

    siwes_status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending Verification"
    )

    duration_months = db.Column(db.Integer)
    eligible_level = db.Column(db.String(100))
    semester = db.Column(db.String(100))

    required_forms = db.Column(db.Text)
    special_requirements = db.Column(db.Text)

    verification_source = db.Column(db.Text)
    last_verified = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    programme = db.relationship(
        "Programme",
        backref=db.backref(
            "siwes_configuration",
            uselist=False
        )
    )