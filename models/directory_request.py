"""
Academic Directory Request Model
--------------------------------
Stores user requests for academic directory records that are missing from DSA.

Requests are review records only. Submitting or approving a request does not
automatically create or verify an Institution, AcademicUnit, Department, or
Programme. Authoritative directory records remain separate.
"""

from datetime import datetime

from .db import db


class DirectoryRequest(db.Model):
    __tablename__ = "directory_requests"

    TYPE_INSTITUTION = "Institution"
    TYPE_PROGRAMME = "Programme"

    REQUEST_TYPE_CHOICES = [
        TYPE_INSTITUTION,
        TYPE_PROGRAMME,
    ]

    STATUS_SUBMITTED = "Submitted"
    STATUS_UNDER_REVIEW = "Under Review"
    STATUS_MORE_INFO_REQUIRED = "More Info Required"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_WITHDRAWN = "Withdrawn"

    STATUS_CHOICES = [
        STATUS_SUBMITTED,
        STATUS_UNDER_REVIEW,
        STATUS_MORE_INFO_REQUIRED,
        STATUS_APPROVED,
        STATUS_REJECTED,
        STATUS_WITHDRAWN,
    ]

    id = db.Column(db.Integer, primary_key=True)

    # ------------------------------------------------------------------
    # Requester
    # ------------------------------------------------------------------

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    request_type = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Existing directory context
    # ------------------------------------------------------------------

    # Programme requests should reference an existing institution where
    # possible. Institution requests leave this field empty because the
    # institution does not yet exist in DSA's controlled directory.
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Requested academic information
    # ------------------------------------------------------------------

    institution_name = db.Column(
        db.String(200),
        nullable=False,
    )

    institution_type = db.Column(
        db.String(100),
        nullable=True,
    )

    city = db.Column(
        db.String(100),
        nullable=True,
    )

    state = db.Column(
        db.String(100),
        nullable=True,
    )

    official_website = db.Column(
        db.String(255),
        nullable=True,
    )

    academic_unit_name = db.Column(
        db.String(200),
        nullable=True,
    )

    academic_unit_type = db.Column(
        db.String(50),
        nullable=True,
    )

    department_name = db.Column(
        db.String(200),
        nullable=True,
    )

    programme_name = db.Column(
        db.String(200),
        nullable=True,
    )

    award = db.Column(
        db.String(100),
        nullable=True,
    )

    # Evidence may be an official webpage, handbook reference, or other
    # information that helps an administrator verify the request.
    evidence_reference = db.Column(
        db.String(500),
        nullable=True,
    )

    requester_notes = db.Column(
        db.Text,
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
            "directory_requests",
            lazy="dynamic",
        ),
    )

    reviewed_by = db.relationship(
        "User",
        foreign_keys=[reviewed_by_user_id],
    )

    institution = db.relationship(
        "Institution",
        backref=db.backref(
            "directory_requests",
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

    def __repr__(self):
        return (
            f"<DirectoryRequest "
            f"User:{self.user_id} "
            f"Type:{self.request_type} "
            f"Status:{self.status}>"
        )
