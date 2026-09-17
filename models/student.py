"""
Student Profile Model
---------------------
Stores SIWES student demographic, academic, and placement preference data.

Academic identity is progressively moving to the structured hierarchy:

Institution -> Academic Unit -> Department -> Programme

The legacy university, faculty, and department text fields are retained
temporarily for backward compatibility with existing records and UI.
"""

from datetime import datetime
from .db import db


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        unique=True,
    )

    # Authoritative structured academic link where available.
    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id"),
        nullable=True,
    )

    # Flexible academic stage. Examples:
    # "300 Level", "400 Level", "ND I", "ND II", "NCE II", "Year 2".
    level = db.Column(db.String(50), nullable=True)

    siwes_session = db.Column(db.String(100), nullable=True)

    full_name = db.Column(db.String(120), nullable=False)
    matric_no = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Legacy compatibility fields.
    # These remain until existing profile routes/templates/data have been
    # safely migrated to the structured academic hierarchy.
    department = db.Column(db.String(120), nullable=False)
    faculty = db.Column(db.String(120), nullable=False)
    university = db.Column(db.String(150), nullable=False)

    # Location preferences
    preferred_state = db.Column(db.String(60), nullable=False)
    preferred_city = db.Column(db.String(80), nullable=False)

    # Career & placement preferences
    area_of_interest = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.Text, nullable=True)
    preferred_org_type = db.Column(db.String(100), nullable=False)

    # Bio / summary for placement requests
    bio = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    saved_organizations = db.relationship(
        "SavedOrganization",
        backref="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    applications = db.relationship(
        "PlacementApplication",
        backref="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    user = db.relationship(
        "User",
        backref=db.backref("student_profile", uselist=False),
    )

    programme = db.relationship(
        "Programme",
        backref=db.backref("student_profiles", lazy=True),
    )

    @property
    def structured_department(self):
        """Return the Department linked through the selected programme."""
        return self.programme.department if self.programme else None

    @property
    def academic_unit(self):
        """Return the Faculty/School/College/etc. for the selected programme."""
        department = self.structured_department
        return department.academic_unit if department else None

    @property
    def institution(self):
        """Return the Institution linked through the selected programme."""
        unit = self.academic_unit
        return unit.institution if unit else None

    @property
    def siwes_configuration(self):
        """Return the programme-level SIWES configuration where available."""
        return self.programme.siwes_configuration if self.programme else None

    @property
    def academic_department_name(self):
        """Prefer structured department data, with legacy data as fallback."""
        department = self.structured_department
        return department.name if department else self.department

    @property
    def academic_unit_name(self):
        """Prefer structured academic-unit data, with legacy data as fallback."""
        unit = self.academic_unit
        return unit.name if unit else self.faculty

    @property
    def institution_name(self):
        """Prefer structured institution data, with legacy data as fallback."""
        institution = self.institution
        return institution.name if institution else self.university

    def __repr__(self):
        return f"<StudentProfile {self.matric_no} - {self.full_name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "matric_no": self.matric_no,

            # Structured academic identity
            "programme_id": self.programme_id,
            "programme": self.programme.name if self.programme else None,
            "award": self.programme.award if self.programme else None,
            "level": self.level,
            "siwes_session": self.siwes_session,
            "department": self.academic_department_name,
            "academic_unit": self.academic_unit_name,
            "institution": self.institution_name,

            # Legacy keys retained for compatibility.
            "faculty": self.academic_unit_name,
            "university": self.institution_name,

            "preferred_state": self.preferred_state,
            "preferred_city": self.preferred_city,
            "area_of_interest": self.area_of_interest,
            "skills": (
                [skill.strip() for skill in self.skills.split(",") if skill.strip()]
                if self.skills
                else []
            ),
            "preferred_org_type": self.preferred_org_type,
            "bio": self.bio,
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M")
                if self.created_at
                else None
            ),
        }
