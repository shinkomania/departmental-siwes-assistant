"""
Academic Directory Request Review Service
-----------------------------------------
Secures Platform Admin review-state transitions for DirectoryRequest.

DirectoryRequest approval/review state is separate from authoritative
academic-directory creation or verification.
"""

from datetime import datetime

from models.db import db
from models.directory_request import DirectoryRequest, DirectoryRequestMessage
from services.authorization import user_has_permission
from services.notification_service import create_notification


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

    clarification_message = DirectoryRequestMessage(
        directory_request_id=directory_request.id,
        author_user_id=reviewer_user.id,
        author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
        message=reviewer_notes,
    )
    db.session.add(clarification_message)

    create_notification(
        recipient_user=directory_request.user,
        category="Directory & Reviews",
        notification_type="directory_clarification_requested",
        title="Additional information required",
        message=(
            "Additional information is required for your academic directory "
            "request. Open the request to review the update and respond."
        ),
        priority="Important",
        action_url=f"/academic/directory-requests/{directory_request.id}",
        source_type="DirectoryRequest",
        source_id=directory_request.id,
        commit=False,
    )

    _commit()
    return directory_request

def respond_to_directory_request_more_information(
    directory_request,
    requester_user,
    message,
    evidence_reference=None,
):
    """
    Submit requester clarification and return the request to its assigned
    reviewer without changing review ownership.
    """
    _require_persisted_request(directory_request)

    if requester_user is None or getattr(requester_user, "id", None) is None:
        raise DirectoryRequestReviewError("Requester user is required.")

    if directory_request.user_id != requester_user.id:
        raise DirectoryRequestReviewError(
            "You cannot respond to another user's directory request."
        )

    _require_status(
        directory_request,
        {DirectoryRequest.STATUS_MORE_INFO_REQUIRED},
        "responded to with additional information",
    )

    message = (message or "").strip()
    if not message:
        raise DirectoryRequestReviewError(
            "Clarification message is required."
        )

    evidence_reference = (evidence_reference or "").strip() or None

    directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW

    clarification_message = DirectoryRequestMessage(
        directory_request_id=directory_request.id,
        author_user_id=requester_user.id,
        author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
        message=message,
        evidence_reference=evidence_reference,
    )
    db.session.add(clarification_message)

    create_notification(
        recipient_user=directory_request.reviewed_by,
        category="Directory & Reviews",
        notification_type="directory_clarification_response_received",
        title="Directory request response received",
        message=(
            "A requester has submitted additional information for an academic "
            "directory request assigned to you."
        ),
        priority="Important",
        action_url=f"/admin/directory-requests/{directory_request.id}",
        source_type="DirectoryRequest",
        source_id=directory_request.id,
        commit=False,
    )

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

    create_notification(
        recipient_user=directory_request.user,
        category="Directory & Reviews",
        notification_type="directory_request_approved",
        title="Directory request approved",
        message=(
            "Your academic directory request has been approved. Approval does "
            "not by itself publish or verify an academic directory record."
        ),
        priority="Normal",
        action_url=f"/academic/directory-requests/{directory_request.id}",
        source_type="DirectoryRequest",
        source_id=directory_request.id,
        commit=False,
    )

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

    create_notification(
        recipient_user=directory_request.user,
        category="Directory & Reviews",
        notification_type="directory_request_rejected",
        title="Directory request not approved",
        message=(
            "Your academic directory request was not approved. Open the "
            "request to review its current status and reviewer information."
        ),
        priority="Important",
        action_url=f"/academic/directory-requests/{directory_request.id}",
        source_type="DirectoryRequest",
        source_id=directory_request.id,
        commit=False,
    )

    _commit()
    return directory_request

def withdraw_directory_request(directory_request, requester_user):
    """
    Withdraw an open DirectoryRequest owned by the requester.

    Withdrawal closes the request while preserving its review and
    clarification history. It does not modify the authoritative
    academic directory.
    """
    _require_persisted_request(directory_request)

    if requester_user is None or getattr(requester_user, "id", None) is None:
        raise DirectoryRequestReviewError("Requester user is required.")

    if directory_request.user_id != requester_user.id:
        raise DirectoryRequestReviewError(
            "You cannot withdraw another user's directory request."
        )

    _require_status(
        directory_request,
        {
            DirectoryRequest.STATUS_SUBMITTED,
            DirectoryRequest.STATUS_UNDER_REVIEW,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        },
        "withdrawn",
    )

    directory_request.withdraw()

    _commit()
    return directory_request
