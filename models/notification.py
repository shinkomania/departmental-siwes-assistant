"""
DSA Notification Model
----------------------
Stores reusable in-app notifications for authenticated DSA users.

Notifications belong to User rather than StudentProfile so the same
foundation can serve students, coordinators, institution staff,
Platform Administrators, and future approved roles/workspaces.

A notification action is navigation only. Authorization must always be
enforced independently by the destination route.
"""

from datetime import datetime

from .db import db


class Notification(db.Model):
    __tablename__ = "notifications"

    CATEGORY_DIRECTORY = "Directory & Reviews"
    CATEGORY_PLACEMENT = "Placements"
    CATEGORY_SIWES = "SIWES"
    CATEGORY_OFFICIAL_NOTICE = "Official Notices"
    CATEGORY_ACCESS_SECURITY = "Access & Security"
    CATEGORY_ORGANIZATION = "Organizations"
    CATEGORY_SYSTEM = "System"

    CATEGORY_CHOICES = [
        CATEGORY_DIRECTORY,
        CATEGORY_PLACEMENT,
        CATEGORY_SIWES,
        CATEGORY_OFFICIAL_NOTICE,
        CATEGORY_ACCESS_SECURITY,
        CATEGORY_ORGANIZATION,
        CATEGORY_SYSTEM,
    ]

    PRIORITY_NORMAL = "Normal"
    PRIORITY_IMPORTANT = "Important"
    PRIORITY_URGENT = "Urgent"

    PRIORITY_CHOICES = [
        PRIORITY_NORMAL,
        PRIORITY_IMPORTANT,
        PRIORITY_URGENT,
    ]

    id = db.Column(db.Integer, primary_key=True)

    recipient_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    category = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    notification_type = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    title = db.Column(
        db.String(255),
        nullable=False,
    )

    message = db.Column(
        db.Text,
        nullable=False,
    )

    priority = db.Column(
        db.String(50),
        nullable=False,
        default=PRIORITY_NORMAL,
        index=True,
    )

    action_url = db.Column(
        db.String(500),
        nullable=True,
    )

    source_type = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    source_id = db.Column(
        db.Integer,
        nullable=True,
        index=True,
    )

    read_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    recipient = db.relationship(
        "User",
        foreign_keys=[recipient_user_id],
        backref=db.backref(
            "notifications",
            lazy="dynamic",
        ),
    )

    @property
    def is_read(self):
        return self.read_at is not None
