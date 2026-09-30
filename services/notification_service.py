"""
DSA Notification Service
------------------------
Provides the reusable application-level API for creating and managing
in-app notifications.

Notification inbox operations are recipient-scoped by construction:
a user must never be able to read or mutate another user's notification.

Notification action URLs are navigation hints only. Destination routes
must independently enforce authentication, ownership, role, permission,
and scope requirements.
"""

from datetime import datetime
from urllib.parse import urlsplit

from models.db import db
from models.notification import Notification
from models.user import User


ACTIVE_ACCOUNT_STATUS = "Active"


class NotificationServiceError(ValueError):
    """Raised when a notification operation is invalid or not permitted."""


def _utcnow():
    return datetime.utcnow()


def _commit():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _require_persisted_user(user):
    if user is None or getattr(user, "id", None) is None:
        raise NotificationServiceError("Recipient user is required.")

    persisted_user = db.session.get(User, user.id)

    if persisted_user is None:
        raise NotificationServiceError("Recipient user does not exist.")

    return persisted_user


def _require_active_user(user):
    persisted_user = _require_persisted_user(user)

    if persisted_user.account_status != ACTIVE_ACCOUNT_STATUS:
        raise NotificationServiceError("User account is not active.")

    return persisted_user


def _clean_required_text(value, field_name):
    value = (value or "").strip()

    if not value:
        raise NotificationServiceError(f"{field_name} is required.")

    return value


def _validate_category(category):
    if category not in Notification.CATEGORY_CHOICES:
        raise NotificationServiceError("Unsupported notification category.")

    return category


def _validate_priority(priority):
    priority = priority or Notification.PRIORITY_NORMAL

    if priority not in Notification.PRIORITY_CHOICES:
        raise NotificationServiceError("Unsupported notification priority.")

    return priority


def _validate_action_url(action_url):
    action_url = (action_url or "").strip() or None

    if action_url is None:
        return None

    parsed = urlsplit(action_url)

    if (
        parsed.scheme
        or parsed.netloc
        or not action_url.startswith("/")
        or action_url.startswith("//")
    ):
        raise NotificationServiceError(
            "Notification action must be an internal DSA path."
        )

    return action_url


def _validate_source_metadata(source_type, source_id):
    source_type = (source_type or "").strip() or None

    if source_id is not None:
        try:
            source_id = int(source_id)
        except (TypeError, ValueError):
            raise NotificationServiceError(
                "Notification source ID must be a positive integer."
            )

        if source_id <= 0:
            raise NotificationServiceError(
                "Notification source ID must be a positive integer."
            )

    if (source_type is None) != (source_id is None):
        raise NotificationServiceError(
            "Notification source type and source ID must be provided together."
        )

    return source_type, source_id


def create_notification(
    recipient_user,
    category,
    notification_type,
    title,
    message,
    priority=Notification.PRIORITY_NORMAL,
    action_url=None,
    source_type=None,
    source_id=None,
    commit=True,
):
    """
    Create a reusable notification for one active DSA user.

    commit=False allows a calling domain service to include the notification
    in its own transaction so the business event and notification can succeed
    or fail together.
    """
    recipient_user = _require_active_user(recipient_user)
    category = _validate_category(category)
    notification_type = _clean_required_text(
        notification_type,
        "Notification type",
    )
    title = _clean_required_text(title, "Notification title")
    message = _clean_required_text(message, "Notification message")
    priority = _validate_priority(priority)
    action_url = _validate_action_url(action_url)
    source_type, source_id = _validate_source_metadata(
        source_type,
        source_id,
    )

    notification = Notification(
        recipient_user_id=recipient_user.id,
        category=category,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        action_url=action_url,
        source_type=source_type,
        source_id=source_id,
    )

    db.session.add(notification)

    if commit:
        _commit()
    else:
        db.session.flush()

    return notification


def get_notifications_for_user(user, limit=None):
    """Return only notifications belonging to the supplied active user."""
    user = _require_active_user(user)

    query = Notification.query.filter_by(
        recipient_user_id=user.id,
    ).order_by(
        Notification.created_at.desc(),
        Notification.id.desc(),
    )

    if limit is not None:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise NotificationServiceError(
                "Notification limit must be a positive integer."
            )

        if limit <= 0:
            raise NotificationServiceError(
                "Notification limit must be a positive integer."
            )

        query = query.limit(limit)

    return query.all()


def get_unread_count_for_user(user):
    """Count unread notifications belonging only to the supplied user."""
    user = _require_active_user(user)

    return Notification.query.filter(
        Notification.recipient_user_id == user.id,
        Notification.read_at.is_(None),
    ).count()


def get_notification_for_user(user, notification_id):
    """
    Return one notification only when it belongs to the supplied user.

    Returning None for a foreign or missing notification avoids exposing
    whether another user's notification ID exists.
    """
    user = _require_active_user(user)

    try:
        notification_id = int(notification_id)
    except (TypeError, ValueError):
        return None

    if notification_id <= 0:
        return None

    return Notification.query.filter_by(
        id=notification_id,
        recipient_user_id=user.id,
    ).first()


def mark_notification_read(user, notification_id):
    """
    Mark one owned notification as read.

    A foreign or missing notification returns None and is never mutated.
    """
    notification = get_notification_for_user(
        user,
        notification_id,
    )

    if notification is None:
        return None

    if notification.read_at is None:
        notification.read_at = _utcnow()
        _commit()

    return notification


def mark_all_notifications_read(user):
    """
    Mark only the supplied user's unread notifications as read.

    Returns the number of notifications changed.
    """
    user = _require_active_user(user)

    unread_notifications = Notification.query.filter(
        Notification.recipient_user_id == user.id,
        Notification.read_at.is_(None),
    ).all()

    if not unread_notifications:
        return 0

    read_at = _utcnow()

    for notification in unread_notifications:
        notification.read_at = read_at

    _commit()
    return len(unread_notifications)
