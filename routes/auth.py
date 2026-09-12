"""
Authentication Routes Blueprint
-------------------------------
Handles account registration, login, and logout for DSA users.

This is the foundation for the unified User authentication system.
Administrative privileges are never granted by registration.
"""

from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models.db import db
from models.user import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_redirect_url(target):
    """
    Allow redirects only to URLs on this application.

    Prevents an attacker from supplying an external URL through ?next=.
    """
    if not target:
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in ("http", "https")
        and host_url.netloc == redirect_url.netloc
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Create a normal DSA user account.

    Registration never grants coordinator, institution administrator,
    SIWES officer, or platform administrator permissions.
    """
    if session.get("user_id"):
        return redirect(url_for("main.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name:
            flash("Please enter your full name.", "danger")
            return render_template("auth/register.html")

        if not email:
            flash("Please enter your email address.", "danger")
            return render_template("auth/register.html")

        if not password:
            flash("Please enter a password.", "danger")
            return render_template("auth/register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("The passwords do not match.", "danger")
            return render_template("auth/register.html")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash(
                "An account already exists with that email address.",
                "warning",
            )
            return render_template("auth/register.html")

        user = User(
            full_name=full_name,
            email=email,
            phone=phone or None,
            account_status="Active",
            email_verified=False,
        )
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash(
                "We could not create your account. Please try again.",
                "danger",
            )
            return render_template("auth/register.html")

        # Start authenticated session immediately.
        session.clear()
        session["user_id"] = user.id

        flash(
            "Your DSA account has been created successfully.",
            "success",
        )

        return redirect(url_for("main.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a DSA user using email and password."""
    if session.get("user_id"):
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        valid_credentials = (
            user is not None
            and user.check_password(password)
        )

        if not valid_credentials:
            flash("Invalid email address or password.", "danger")
            return render_template("auth/login.html")

        if user.account_status != "Active":
            flash(
                "This account is currently unavailable. "
                "Please contact DSA support.",
                "warning",
            )
            return render_template("auth/login.html")

        session.clear()
        session["user_id"] = user.id

        flash(f"Welcome back, {user.full_name}.", "success")

        next_page = request.args.get("next")

        if next_page and _is_safe_redirect_url(next_page):
            return redirect(next_page)

        return redirect(url_for("main.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """End the current authenticated DSA session."""
    session.clear()

    flash("You have been logged out successfully.", "info")

    return redirect(url_for("main.index"))