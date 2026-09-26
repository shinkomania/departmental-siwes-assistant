"""
Academic Directory Request Review Service
-----------------------------------------
Secures Platform Admin review-state transitions for DirectoryRequest.

DirectoryRequest approval/review state is separate from authoritative
academic-directory creation or verification.
"""

from datetime import datetime

from models.db import db
from models.directory_request import DirectoryRequest
from services.authorization import user_has_permission


PLATFORM_ADMIN_PERMISSION = "access_platform_admin_panel"
ACTIVE_ACCOUNT_STATUS = "Active"

MARK_UNDER_REVIEW_FROM = {
    DirectoryRequest.STATUS_SUBMITTED,
}


REQUEST_MORE_INFO_FROM = {
    DirectoryRequest.STATUS_UNDER_REVIEW,
}

APPROVE_FROM = {
    DirectoryRequest.STATUS_UNDER_REVIEW,
}

REJECT_FROM = {
    DirectoryRequest.STATUS_UNDER_REVIEW,
}


class DirectoryRequestReviewError(ValueError):
    """Raised when a DirectoryRequest review action is not permitted."""


def _utcnow():
    return datetime.utcnow()


def _require_persisted_request(directory_request):
    if directory_request is None or getattr(directory_request, "id", None) is None:
        raise DirectoryRequestReviewError("Directory request is required.")


def _require_platform_admin(reviewer_user):
    if reviewer_user is None or getattr(reviewer_user, "id", None) is None:
        raise DirectoryRequestReviewError("Reviewer user is required.")

    if getattr(reviewer_user, "account_status", None) != ACTIVE_ACCOUNT_STATUS:
        raise DirectoryRequestReviewError("Reviewer user account is not active.")

    if not user_has_permission(reviewer_user, PLATFORM_ADMIN_PERMISSION):
        raise DirectoryRequestReviewError(
            "Reviewer is not authorized to review academic directory requests."
        )


def _require_status(directory_request, allowed_statuses, action_label):
    if directory_request.status not in allowed_statuses:
        raise DirectoryRequestReviewError(
            f"Directory request cannot be {action_label} from status "
            f"'{directory_request.status}'."
        )


def _require_review_owner(directory_request, reviewer_user):
    """Require the active reviewer to own the current review cycle."""
    if directory_request.reviewed_by_user_id != reviewer_user.id:
        raise DirectoryRequestReviewError(
            "This directory request is currently assigned to another reviewer."
        )

def _commit():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def mark_directory_request_under_review(directory_request, reviewer_user):
    """Move a submitted DirectoryRequest into Under Review."""
    _require_persisted_request(directory_request)
    _require_platform_admin(reviewer_user)
    _require_status(
        directory_request,
        MARK_UNDER_REVIEW_FROM,
        "marked under review",
    )

    directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
    directory_request.review_started_at = _utcnow()
    directory_request.reviewed_by_user_id = reviewer_user.id

    _commit()
    return directory_request


def request_directory_request_more_information(
    directory_request,
    reviewer_user,
    reviewer_notes,
):
    """Request additional information for a DirectoryRequest under review."""
    _require_persisted_request(directory_request)
    _require_platform_admin(reviewer_user)
    _require_status(
        directory_request,
        REQUEST_MORE_INFO_FROM,
        "sent back for more information",
    )
    _require_review_owner(directory_request, reviewer_user)

    reviewer_notes = (reviewer_notes or "").strip()
    if not reviewer_notes:
        raise DirectoryRequestReviewError(
            "Reviewer notes are required when requesting more information."
        )

    directory_request.status = DirectoryRequest.STATUS_MORE_INFO_REQUIRED
    directory_request.reviewed_by_user_id = reviewer_user.id
    directory_request.reviewer_notes = reviewer_notes

    if directory_request.review_started_at is None:
        directory_request.review_started_at = _utcnow()

    _commit()
    return directory_request

def approve_directory_request(
    directory_request,
    reviewer_user,
    reviewer_notes=None,
):
    """Approve a DirectoryRequest under review without modifying the directory."""
    _require_persisted_request(directory_request)
    _require_platform_admin(reviewer_user)
    _require_status(
        directory_request,
        APPROVE_FROM,
        "approved",
    )
    _require_review_owner(directory_request, reviewer_user)

    reviewer_notes = (reviewer_notes or "").strip() or None

    directory_request.status = DirectoryRequest.STATUS_APPROVED
    directory_request.reviewed_by_user_id = reviewer_user.id
    directory_request.reviewer_notes = reviewer_notes

    if directory_request.review_started_at is None:
        directory_request.review_started_at = _utcnow()

    directory_request.decided_at = _utcnow()

    _commit()
    return directory_request

def reject_directory_request(
    directory_request,
    reviewer_user,
    reviewer_notes,
):
    """Reject a DirectoryRequest under review without modifying the directory."""
    _require_persisted_request(directory_request)
    _require_platform_admin(reviewer_user)
    _require_status(
        directory_request,
        REJECT_FROM,
        "rejected",
    )
    _require_review_owner(directory_request, reviewer_user)

    reviewer_notes = (reviewer_notes or "").strip()
    if not reviewer_notes:
        raise DirectoryRequestReviewError(
            "Reviewer notes are required when rejecting a directory request."
        )

    directory_request.status = DirectoryRequest.STATUS_REJECTED
    directory_request.reviewed_by_user_id = reviewer_user.id
    directory_request.reviewer_notes = reviewer_notes

    if directory_request.review_started_at is None:
        directory_request.review_started_at = _utcnow()

    directory_request.decided_at = _utcnow()

    _commit()
    return directory_request
