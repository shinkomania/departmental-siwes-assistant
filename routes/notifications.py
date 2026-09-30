"""
DSA Notification Routes
-----------------------
Provides the authenticated account-level notification centre.

Notification ownership is always derived from session['user_id'].
A notification identifier supplied by the browser never determines
which user's inbox may be read or changed.
"""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)

from models.db import db
from models.user import User
from services.notification_service import (
    NotificationServiceError,
    get_notification_for_user,
    get_notifications_for_user,
    mark_all_notifications_read,
    mark_notification_read,
)


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications",
)


def _current_user():
    """Return the authenticated active User or None."""
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if user is None or user.account_status != "Active":
        return None

    return user


def _require_authenticated_user():
    """
    Require an active authenticated account.

    Keep the original destination so a future login-flow improvement can
    safely return the user after authentication.
    """
    user = _current_user()

    if user is None:
        return None

    return user


@notifications_bp.route("/")
def notification_centre():
    """Display only the authenticated user's notification inbox."""
    user = _require_authenticated_user()

    if user is None:
        flash("Please sign in to view your notifications.", "info")
        return redirect(url_for("auth.login"))

    try:
        notifications = get_notifications_for_user(user)
    except NotificationServiceError:
        abort(403)

    unread_count = sum(
        1 for notification in notifications
        if not notification.is_read
    )

    return render_template(
        "notifications/index.html",
        notifications=notifications,
        unread_count=unread_count,
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
def mark_read(notification_id):
    """Mark one owned notification as read."""
    user = _require_authenticated_user()

    if user is None:
        flash("Please sign in to manage your notifications.", "info")
        return redirect(url_for("auth.login"))

    notification = get_notification_for_user(
        user,
        notification_id,
    )

    if notification is None:
        abort(404)

    mark_notification_read(
        user,
        notification.id,
    )

    return redirect(url_for("notifications.notification_centre"))


@notifications_bp.route("/read-all", methods=["POST"])
def mark_all_read():
    """Mark only the authenticated user's notifications as read."""
    user = _require_authenticated_user()

    if user is None:
        flash("Please sign in to manage your notifications.", "info")
        return redirect(url_for("auth.login"))

    changed = mark_all_notifications_read(user)

    if changed:
        flash(
            f"{changed} notification{'s' if changed != 1 else ''} marked as read.",
            "success",
        )

    return redirect(url_for("notifications.notification_centre"))


@notifications_bp.route("/<int:notification_id>/open", methods=["POST"])
def open_notification(notification_id):
    """
    Mark an owned notification as read and navigate to its internal action.

    The action URL is only navigation. The destination route remains
    responsible for its own authorization and scope checks.
    """
    user = _require_authenticated_user()

    if user is None:
        flash("Please sign in to open notifications.", "info")
        return redirect(url_for("auth.login"))

    notification = get_notification_for_user(
        user,
        notification_id,
    )

    if notification is None:
        abort(404)

    mark_notification_read(
        user,
        notification.id,
    )

    action_url = notification.action_url

    if action_url:
        return redirect(action_url)

    return redirect(url_for("notifications.notification_centre"))
