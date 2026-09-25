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
