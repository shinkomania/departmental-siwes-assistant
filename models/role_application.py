"""
Administrative Role Application Model
-------------------------------------
Stores requests for privileged DSA roles such as:

- Primary Institution Administrator
- Institution SIWES Officer
- Departmental SIWES Coordinator

Important:
An approved application does NOT itself grant access.
Access is granted separately through UserRoleAssignment after approval.
"""

from datetime import datetime

from .db import db


class RoleApplication(db.Model):
    __tablename__ = "role_applications"

    STATUS_SUBMITTED = "Submitted"
    STATUS_PENDING_VERIFICATION = "Pending Verification"
    STATUS_UNDER_REVIEW = "Under Review"
    STATUS_MORE_INFO_REQUIRED = "More Info Required"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_WITHDRAWN = "Withdrawn"

    STATUS_CHOICES = [
        STATUS_SUBMITTED,
        STATUS_PENDING_VERIFICATION,
        STATUS_UNDER_REVIEW,
        STATUS_MORE_INFO_REQUIRED,
        STATUS_APPROVED,
        STATUS_REJECTED,
        STATUS_WITHDRAWN,
    ]

    VERIFICATION_METHOD_CHOICES = [
        "Institution Administrator Confirmation",
        "Appointment Letter",
        "Departmental Confirmation",
        "Staff ID and Supporting Evidence",
        "Official Institutional Email",
        "Other Official Evidence",
    ]

    id = db.Column(db.Integer, primary_key=True)

    # ------------------------------------------------------------------
    # Applicant and requested role
    # ------------------------------------------------------------------

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    requested_role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Requested scope
    # ------------------------------------------------------------------

    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id"),
        nullable=False,
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

    academic_session = db.Column(
        db.String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Applicant-provided professional information
    # ------------------------------------------------------------------

    official_position = db.Column(
        db.String(200),
        nullable=False,
    )

    institutional_email = db.Column(
        db.String(255),
        nullable=True,
    )

    phone = db.Column(
        db.String(50),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Verification information
    # ------------------------------------------------------------------

    verification_method = db.Column(
        db.String(150),
        nullable=True,
    )

    evidence_reference = db.Column(
        db.String(500),
        nullable=True,
    )

    evidence_notes = db.Column(
        db.Text,
        nullable=True,
    )

    # Future document-storage integration can attach a secure document
    # reference here without exposing a public file URL.
    evidence_file_reference = db.Column(
        db.String(500),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Review workflow
    # ------------------------------------------------------------------

    status = db.Column(
        db.String(50),
        nullable=False,
        default=STATUS_SUBMITTED,
        index=True,
    )

    applicant_notes = db.Column(
        db.Text,
        nullable=True,
    )

    reviewer_notes = db.Column(
        db.Text,
        nullable=True,
    )

    reviewed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    submitted_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    review_started_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    decided_at = db.Column(
        db.DateTime,
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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref(
            "role_applications",
            lazy="dynamic",
        ),
    )

    reviewed_by = db.relationship(
        "User",
        foreign_keys=[reviewed_by_user_id],
    )

    requested_role = db.relationship(
        "Role",
        backref=db.backref(
            "role_applications",
            lazy="dynamic",
        ),
    )

    institution = db.relationship(
        "Institution",
        backref=db.backref(
            "role_applications",
            lazy="dynamic",
        ),
    )

    department = db.relationship(
        "Department",
        backref=db.backref(
            "role_applications",
            lazy="dynamic",
        ),
    )

    programme = db.relationship(
        "Programme",
        backref=db.backref(
            "role_applications",
            lazy="dynamic",
        ),
    )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_open(self):
        return self.status in {
            self.STATUS_SUBMITTED,
            self.STATUS_PENDING_VERIFICATION,
            self.STATUS_UNDER_REVIEW,
            self.STATUS_MORE_INFO_REQUIRED,
        }

    @property
    def is_final(self):
        return self.status in {
            self.STATUS_APPROVED,
            self.STATUS_REJECTED,
            self.STATUS_WITHDRAWN,
        }

    def mark_under_review(self, reviewer_user_id=None):
        self.status = self.STATUS_UNDER_REVIEW
        self.review_started_at = datetime.utcnow()

        if reviewer_user_id is not None:
            self.reviewed_by_user_id = reviewer_user_id

    def approve(self, reviewer_user_id, reviewer_notes=None):
        self.status = self.STATUS_APPROVED
        self.reviewed_by_user_id = reviewer_user_id
        self.reviewer_notes = reviewer_notes
        self.decided_at = datetime.utcnow()

    def reject(self, reviewer_user_id, reviewer_notes=None):
        self.status = self.STATUS_REJECTED
        self.reviewed_by_user_id = reviewer_user_id
        self.reviewer_notes = reviewer_notes
        self.decided_at = datetime.utcnow()

    def request_more_information(self, reviewer_user_id, reviewer_notes=None):
        self.status = self.STATUS_MORE_INFO_REQUIRED
        self.reviewed_by_user_id = reviewer_user_id
        self.reviewer_notes = reviewer_notes

    def withdraw(self):
        self.status = self.STATUS_WITHDRAWN
        self.decided_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "requested_role_id": self.requested_role_id,
            "requested_role": (
                self.requested_role.slug
                if self.requested_role
                else None
            ),
            "institution_id": self.institution_id,
            "department_id": self.department_id,
            "programme_id": self.programme_id,
            "academic_session": self.academic_session,
            "official_position": self.official_position,
            "institutional_email": self.institutional_email,
            "phone": self.phone,
            "verification_method": self.verification_method,
            "status": self.status,
            "submitted_at": (
                self.submitted_at.isoformat()
                if self.submitted_at
                else None
            ),
            "review_started_at": (
                self.review_started_at.isoformat()
                if self.review_started_at
                else None
            ),
            "decided_at": (
                self.decided_at.isoformat()
                if self.decided_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<RoleApplication "
            f"User:{self.user_id} "
            f"Role:{self.requested_role_id} "
            f"Status:{self.status}>"
        )
