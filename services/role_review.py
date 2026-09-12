"""
Administrative Role Application Review Service
----------------------------------------------
Handles non-approval review actions for privileged DSA role applications.

This service enforces:
- active reviewer/applicant accounts where applicable;
- explicit reviewer permission + institution scope;
- supported administrative role types;
- valid workflow state transitions;
- no reviewer self-review;
- applicant-only withdrawal;
- transactional persistence.

Final approval remains in services.role_approval.
"""

from datetime import datetime

from models.db import db
from models.user import User
from models.role_application import RoleApplication
from services.authorization import user_has_permission


ACTIVE_ACCOUNT_STATUS = "Active"

REVIEW_PERMISSION_BY_ROLE = {
    "primary_institution_administrator": "review_institution_admin_applications",
    "institution_siwes_officer": "review_institution_siwes_officer_applications",
    "departmental_siwes_coordinator": "review_coordinator_applications",
}

REVIEWABLE_STATUSES = {
    RoleApplication.STATUS_SUBMITTED,
    RoleApplication.STATUS_PENDING_VERIFICATION,
    RoleApplication.STATUS_UNDER_REVIEW,
    RoleApplication.STATUS_MORE_INFO_REQUIRED,
}

MARK_UNDER_REVIEW_FROM = {
    RoleApplication.STATUS_SUBMITTED,
    RoleApplication.STATUS_PENDING_VERIFICATION,
    RoleApplication.STATUS_MORE_INFO_REQUIRED,
}

REQUEST_MORE_INFO_FROM = {
    RoleApplication.STATUS_SUBMITTED,
    RoleApplication.STATUS_PENDING_VERIFICATION,
    RoleApplication.STATUS_UNDER_REVIEW,
}

REJECT_FROM = REVIEWABLE_STATUSES

WITHDRAW_FROM = REVIEWABLE_STATUSES


class RoleReviewError(ValueError):
    """Raised when a role-application review action is not permitted."""


def _utcnow():
    return datetime.utcnow()


def _require_persisted_application(application):
    if application is None or getattr(application, "id", None) is None:
        raise RoleReviewError("Role application is required.")


def _require_active_user(user, label):
    if user is None or getattr(user, "id", None) is None:
        raise RoleReviewError(f"{label} user is required.")

    if getattr(user, "account_status", None) != ACTIVE_ACCOUNT_STATUS:
        raise RoleReviewError(f"{label} user account is not active.")


def _required_review_permission(application):
    role = application.requested_role

    if role is None or not role.is_active:
        raise RoleReviewError("Requested role does not exist or is inactive.")

    permission_slug = REVIEW_PERMISSION_BY_ROLE.get(role.slug)

    if permission_slug is None:
        raise RoleReviewError(
            f"Role '{role.slug}' has no administrative review workflow."
        )

    return permission_slug


def _require_reviewer_authorization(application, reviewer_user):
    _require_active_user(reviewer_user, "Reviewer")

    if reviewer_user.id == application.user_id:
        raise RoleReviewError("Applicants cannot review their own applications.")

    permission_slug = _required_review_permission(application)

    if not user_has_permission(
        reviewer_user,
        permission_slug,
        institution_id=application.institution_id,
    ):
        raise RoleReviewError(
            "Reviewer is not authorized to review this application."
        )


def _require_status(application, allowed_statuses, action_label):
    if application.status not in allowed_statuses:
        raise RoleReviewError(
            f"Application cannot be {action_label} from status "
            f"'{application.status}'."
        )


def _commit():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def mark_role_application_under_review(
    application,
    reviewer_user,
):
    """Move an application into Under Review."""
    _require_persisted_application(application)
    _require_reviewer_authorization(application, reviewer_user)
    _require_status(application, MARK_UNDER_REVIEW_FROM, "marked under review")

    application.status = RoleApplication.STATUS_UNDER_REVIEW
    application.review_started_at = _utcnow()
    application.reviewed_by_user_id = reviewer_user.id

    _commit()
    return application


def request_role_application_more_information(
    application,
    reviewer_user,
    reviewer_notes,
):
    """Request more information from the applicant."""
    _require_persisted_application(application)
    _require_reviewer_authorization(application, reviewer_user)
    _require_status(
        application,
        REQUEST_MORE_INFO_FROM,
        "sent back for more information",
    )

    reviewer_notes = (reviewer_notes or "").strip()
    if not reviewer_notes:
        raise RoleReviewError(
            "Reviewer notes are required when requesting more information."
        )

    application.status = RoleApplication.STATUS_MORE_INFO_REQUIRED
    application.reviewed_by_user_id = reviewer_user.id
    application.reviewer_notes = reviewer_notes

    if application.review_started_at is None:
        application.review_started_at = _utcnow()

    _commit()
    return application


def reject_role_application(
    application,
    reviewer_user,
    reviewer_notes,
):
    """Reject an open administrative role application."""
    _require_persisted_application(application)
    _require_reviewer_authorization(application, reviewer_user)
    _require_status(application, REJECT_FROM, "rejected")

    reviewer_notes = (reviewer_notes or "").strip()
    if not reviewer_notes:
        raise RoleReviewError(
            "Reviewer notes are required when rejecting an application."
        )

    now = _utcnow()

    application.status = RoleApplication.STATUS_REJECTED
    application.reviewed_by_user_id = reviewer_user.id
    application.reviewer_notes = reviewer_notes
    application.decided_at = now

    if application.review_started_at is None:
        application.review_started_at = now

    _commit()
    return application


def withdraw_role_application(
    application,
    applicant_user,
):
    """Allow the applicant to withdraw their own open application."""
    _require_persisted_application(application)
    _require_active_user(applicant_user, "Applicant")
    _require_status(application, WITHDRAW_FROM, "withdrawn")

    if applicant_user.id != application.user_id:
        raise RoleReviewError(
            "Only the applicant can withdraw this application."
        )

    application.status = RoleApplication.STATUS_WITHDRAWN
    application.decided_at = _utcnow()

    _commit()
    return application
