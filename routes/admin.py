"""
Platform Administration Routes
------------------------------
Provides the secured DSA Platform Administration interface.

Current responsibilities:
- Platform overview and operational metrics.
- Organization directory management.
- Community organization review queue.
- Organization provenance, review, listing, and intake management.
- SIWES guide management.
- User account administration.
- Privileged role revocation.

Important design rules:
- Platform administration requires an explicit global permission.
- Legacy session flags never grant administrative access.
- Organization review is not presented as employer certification.
- Source/provenance, DSA review state, listing state, and current SIWES
  intake state are separate facts.
- Suspending an account is separate from revoking a privileged role.
"""

from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models.access import UserRoleAssignment
from models.application import PlacementApplication
from models.db import db
from models.guide import GuideTopic
from models.organization import Organization
from models.student import StudentProfile
from models.user import User

from routes.student import (
    AREAS_OF_INTEREST,
    NIGERIAN_STATES,
    ORGANIZATION_TYPES,
)

from services.authorization import user_has_permission


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


PLATFORM_ADMIN_PERMISSION = "access_platform_admin_panel"

ACTIVE_ACCOUNT_STATUS = "Active"
SUSPENDED_ACCOUNT_STATUS = "Suspended"

APPROVED_ASSIGNMENT_STATUS = "Approved"
REVOKED_ASSIGNMENT_STATUS = "Revoked"


def _utcnow():
    """Return a naive UTC datetime compatible with current project models."""
    return datetime.utcnow()


def _current_user():
    """
    Resolve the currently authenticated active user.

    Authentication authority is session['user_id'] only.
    Legacy session['is_admin'] is never trusted.
    """
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if user is None:
        return None

    if user.account_status != ACTIVE_ACCOUNT_STATUS:
        return None

    return user


def _current_platform_administrator():
    """
    Return the authenticated user only when they have the explicit,
    globally-scoped Platform Administration Panel permission.
    """
    user = _current_user()

    if user is None:
        return None

    if not user_has_permission(
        user,
        PLATFORM_ADMIN_PERMISSION,
    ):
        return None

    return user


def admin_required(f):
    """
    Require authenticated platform-administration permission.

    Access is based on:

        User
        -> Approved current role assignment
        -> Explicit permission
        -> Global scope

    Legacy session['is_admin'] is ignored.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = _current_user()

        if user is None:
            flash(
                "Please sign in to access the administration area.",
                "warning",
            )

            return redirect(
                url_for(
                    "auth.login",
                    next=request.url,
                )
            )

        if _current_platform_administrator() is None:
            return (
                "Forbidden: your account does not have permission "
                "to access the platform administration area.",
                403,
            )

        return f(*args, **kwargs)

    return decorated_function


def _parse_date(value):
    """
    Parse an HTML date input into a datetime.

    Empty values are stored as None.
    """
    value = (value or "").strip()

    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _valid_choice(value, choices, default):
    """Return value when allowed, otherwise return the supplied default."""
    if value in choices:
        return value

    return default


def _organization_form_context(org=None):
    """Shared context for organization create/edit forms."""
    org_types = list(ORGANIZATION_TYPES)

    # Preserve legacy/custom industry values when editing existing records.
    if org and org.industry and org.industry not in org_types:
        org_types.append(org.industry)

    return {
        "org": org,
        "states": NIGERIAN_STATES,
        "interests": AREAS_OF_INTEREST,
        "org_types": org_types,
        "source_types": Organization.SOURCE_TYPES,
        "review_statuses": Organization.REVIEW_STATUSES,
        "listing_statuses": Organization.LISTING_STATUSES,
        "acceptance_statuses": Organization.ACCEPTANCE_STATUSES,
    }


def _apply_organization_form(org):
    """
    Apply the modern organization administration form to an Organization.

    The modern provenance fields are authoritative for new admin UI.

    Legacy verification_status/source/why_relevant fields are still maintained
    with neutral compatibility values because the database columns remain
    non-nullable and older code may still reference them during migration.
    """
    org.name = request.form.get("name", "").strip()
    org.description = request.form.get("description", "").strip()
    org.address = request.form.get("address", "").strip()
    org.state = request.form.get("state", "").strip()
    org.city = request.form.get("city", "").strip()
    org.industry = request.form.get("industry", "").strip()
    org.relevance_areas = request.form.get("relevance_areas", "").strip()

    org.website = request.form.get("website", "").strip()
    org.contact_email = request.form.get("contact_email", "").strip()
    org.contact_phone = request.form.get("contact_phone", "").strip()

    source_type = request.form.get("source_type", "Other").strip()
    org.source_type = _valid_choice(
        source_type,
        Organization.SOURCE_TYPES,
        "Other",
    )

    org.source_name = request.form.get("source_name", "").strip() or None
    org.source_url = request.form.get("source_url", "").strip() or None
    org.source_reference = (
        request.form.get("source_reference", "").strip() or None
    )
    org.source_last_checked = _parse_date(
        request.form.get("source_last_checked")
    )
    org.provenance_notes = (
        request.form.get("provenance_notes", "").strip() or None
    )

    previous_review_status = org.review_status

    review_status = request.form.get(
        "review_status",
        org.review_status or "Pending",
    ).strip()

    org.review_status = _valid_choice(
        review_status,
        Organization.REVIEW_STATUSES,
        "Pending",
    )

    if (
        org.review_status == "Reviewed"
        and previous_review_status != "Reviewed"
    ):
        org.reviewed_at = _utcnow()
    elif org.review_status != "Reviewed":
        org.reviewed_at = None

    listing_status = request.form.get(
        "listing_status",
        org.listing_status or "Unknown",
    ).strip()

    org.listing_status = _valid_choice(
        listing_status,
        Organization.LISTING_STATUSES,
        "Unknown",
    )

    acceptance_status = request.form.get(
        "acceptance_status",
        org.acceptance_status or "Unknown",
    ).strip()

    org.acceptance_status = _valid_choice(
        acceptance_status,
        Organization.ACCEPTANCE_STATUSES,
        "Unknown",
    )

    org.acceptance_source_name = (
        request.form.get("acceptance_source_name", "").strip() or None
    )
    org.acceptance_source_url = (
        request.form.get("acceptance_source_url", "").strip() or None
    )
    org.acceptance_last_checked = _parse_date(
        request.form.get("acceptance_last_checked")
    )
    org.acceptance_notes = (
        request.form.get("acceptance_notes", "").strip() or None
    )

    # Directory visibility is deliberately separate from listing/intake claims.
    org.is_active = request.form.get("is_active") == "on"

    # Transitional compatibility only. New UI must not use these as badges.
    org.verification_status = (
        "Pending Review"
        if org.review_status == "Pending"
        else org.review_status
    )
    org.source = org.source_name or org.source_type or "Source not recorded"
    org.why_relevant = org.provenance_notes or ""


@admin_bp.route("/")
@admin_required
def dashboard():
    """Platform Administration overview and operational review queue."""
    total_orgs = Organization.query.count()

    pending_reviews = Organization.query.filter_by(
        review_status="Pending"
    ).count()

    active_listings = Organization.query.filter_by(
        is_active=True,
        listing_status="Active",
    ).count()

    current_intake_evidence = Organization.query.filter(
        Organization.acceptance_status == "Currently Accepting",
        db.or_(
            Organization.acceptance_source_name.isnot(None),
            Organization.acceptance_source_url.isnot(None),
        ),
    ).count()

    total_users = User.query.count()

    suspended_users = User.query.filter_by(
        account_status=SUSPENDED_ACCOUNT_STATUS
    ).count()

    total_students = StudentProfile.query.filter(
        StudentProfile.user_id.isnot(None)
    ).count()
    total_applications = PlacementApplication.query.count()
    guide_topics_count = GuideTopic.query.count()

    recent_pending_reviews = (
        Organization.query
        .filter_by(review_status="Pending")
        .order_by(Organization.created_at.desc())
        .limit(5)
        .all()
    )

    recent_users = (
        User.query
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_orgs=total_orgs,
        pending_reviews=pending_reviews,
        active_listings=active_listings,
        current_intake_evidence=current_intake_evidence,
        total_users=total_users,
        suspended_users=suspended_users,
        total_students=total_students,
        total_applications=total_applications,
        guide_topics_count=guide_topics_count,
        recent_pending_reviews=recent_pending_reviews,
        recent_users=recent_users,
    )


@admin_bp.route("/organizations")
@admin_required
def organizations():
    """
    Browse the organization directory using modern provenance/status filters.
    """
    source_type = request.args.get("source_type", "all").strip()
    review_status = request.args.get("review_status", "all").strip()
    listing_status = request.args.get("listing_status", "all").strip()
    acceptance_status = request.args.get("acceptance_status", "all").strip()
    visibility = request.args.get("visibility", "all").strip()
    search = request.args.get("q", "").strip()

    query = Organization.query

    if source_type in Organization.SOURCE_TYPES:
        query = query.filter_by(source_type=source_type)

    if review_status in Organization.REVIEW_STATUSES:
        query = query.filter_by(review_status=review_status)

    if listing_status in Organization.LISTING_STATUSES:
        query = query.filter_by(listing_status=listing_status)

    if acceptance_status in Organization.ACCEPTANCE_STATUSES:
        query = query.filter_by(acceptance_status=acceptance_status)

    if visibility == "visible":
        query = query.filter_by(is_active=True)
    elif visibility == "hidden":
        query = query.filter_by(is_active=False)

    if search:
        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Organization.name.ilike(search_pattern),
                Organization.city.ilike(search_pattern),
                Organization.state.ilike(search_pattern),
                Organization.industry.ilike(search_pattern),
                Organization.source_name.ilike(search_pattern),
            )
        )

    orgs = query.order_by(Organization.created_at.desc()).all()

    return render_template(
        "admin/organizations.html",
        organizations=orgs,
        source_types=Organization.SOURCE_TYPES,
        review_statuses=Organization.REVIEW_STATUSES,
        listing_statuses=Organization.LISTING_STATUSES,
        acceptance_statuses=Organization.ACCEPTANCE_STATUSES,
        active_source_type=source_type,
        active_review_status=review_status,
        active_listing_status=listing_status,
        active_acceptance_status=acceptance_status,
        active_visibility=visibility,
        search_query=search,
    )


@admin_bp.route("/organizations/review")
@admin_required
def organization_review_queue():
    """Show organization records that still require Platform Admin review."""
    pending_organizations = (
        Organization.query
        .filter_by(review_status="Pending")
        .order_by(Organization.created_at.asc())
        .all()
    )

    return render_template(
        "admin/organizations.html",
        organizations=pending_organizations,
        source_types=Organization.SOURCE_TYPES,
        review_statuses=Organization.REVIEW_STATUSES,
        listing_statuses=Organization.LISTING_STATUSES,
        acceptance_statuses=Organization.ACCEPTANCE_STATUSES,
        active_source_type="all",
        active_review_status="Pending",
        active_listing_status="all",
        active_acceptance_status="all",
        active_visibility="all",
        search_query="",
        review_queue_mode=True,
    )


@admin_bp.route("/organizations/new", methods=["GET", "POST"])
@admin_required
def new_organization():
    """
    Create a new organization record.

    Admin-created records are not automatically described as verified.
    Provenance and evidence states must be recorded explicitly.
    """
    if request.method == "POST":
        org = Organization(
            name="",
            description="",
            state="",
            city="",
            industry="",
            relevance_areas="",
            source_type="Other",
            review_status="Pending",
            listing_status="Unknown",
            acceptance_status="Unknown",
            is_active=False,
            verification_status="Pending Review",
            source="Source not recorded",
        )

        _apply_organization_form(org)

        if not org.name:
            flash("Organization name is required.", "danger")
            return render_template(
                "admin/org_form.html",
                **_organization_form_context(org),
            )

        if not org.description:
            flash("Organization description is required.", "danger")
            return render_template(
                "admin/org_form.html",
                **_organization_form_context(org),
            )

        if not org.state or not org.city or not org.industry:
            flash(
                "State, city/town, and industry/sector are required.",
                "danger",
            )
            return render_template(
                "admin/org_form.html",
                **_organization_form_context(org),
            )

        db.session.add(org)
        db.session.commit()

        flash(
            f'Organization "{org.name}" added to the directory.',
            "success",
        )

        return redirect(url_for("admin.organizations"))

    return render_template(
        "admin/org_form.html",
        **_organization_form_context(),
    )


@admin_bp.route(
    "/organizations/edit/<int:org_id>",
    methods=["GET", "POST"],
)
@admin_required
def edit_organization(org_id):
    """Review or edit an existing organization record."""
    org = Organization.query.get_or_404(org_id)

    if request.method == "POST":
        _apply_organization_form(org)

        if not org.name:
            flash("Organization name is required.", "danger")
            return render_template(
                "admin/org_form.html",
                **_organization_form_context(org),
            )

        if not org.description:
            flash("Organization description is required.", "danger")
            return render_template(
                "admin/org_form.html",
                **_organization_form_context(org),
            )

        if not org.state or not org.city or not org.industry:
            flash(
                "State, city/town, and industry/sector are required.",
                "danger",
            )
            return render_template(
                "admin/org_form.html",
                **_organization_form_context(org),
            )

        db.session.commit()

        flash(
            f'Updated organization record for "{org.name}".',
            "success",
        )

        return redirect(url_for("admin.organizations"))

    return render_template(
        "admin/org_form.html",
        **_organization_form_context(org),
    )


@admin_bp.route(
    "/organizations/verify/<int:org_id>",
    methods=["POST"],
)
@admin_required
def verify_organization(org_id):
    """
    Transitional endpoint retained for route compatibility.

    This action now means:
        "Mark DSA's internal review as completed."

    It does NOT certify the employer, prove current SIWES intake,
    or prove suitability for any specific programme.
    """
    org = Organization.query.get_or_404(org_id)

    org.review_status = "Reviewed"
    org.reviewed_at = _utcnow()

    # Transitional legacy compatibility only.
    org.verification_status = "Reviewed"

    db.session.commit()

    flash(
        f'Review completed for "{org.name}". '
        "Listing and intake states remain separate.",
        "success",
    )

    return redirect(url_for("admin.organization_review_queue"))


@admin_bp.route(
    "/organizations/delete/<int:org_id>",
    methods=["POST"],
)
@admin_required
def delete_organization(org_id):
    """
    Permanently delete an organization record.

    This legacy operation remains available during Phase 3, but the UI should
    present it as a destructive administrative action rather than a normal
    lifecycle control. Inactive/hidden states should normally be preferred.
    """
    org = Organization.query.get_or_404(org_id)
    name = org.name

    db.session.delete(org)
    db.session.commit()

    flash(
        f'Deleted organization "{name}".',
        "info",
    )

    return redirect(url_for("admin.organizations"))


@admin_bp.route("/users")
@admin_required
def users():
    """Browse registered DSA users and their account/access state."""
    status_filter = request.args.get("status", "all").strip()
    search = request.args.get("q", "").strip()

    query = User.query

    if status_filter in (
        ACTIVE_ACCOUNT_STATUS,
        SUSPENDED_ACCOUNT_STATUS,
    ):
        query = query.filter_by(account_status=status_filter)

    if search:
        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.phone.ilike(search_pattern),
            )
        )

    users_list = query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin/users.html",
        users=users_list,
        active_status=status_filter,
        search_query=search,
        current_admin=_current_platform_administrator(),
    )


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    """Inspect one user's account and role assignments."""
    user = User.query.get_or_404(user_id)

    assignments = (
        UserRoleAssignment.query
        .filter_by(user_id=user.id)
        .order_by(UserRoleAssignment.created_at.desc())
        .all()
    )

    return render_template(
        "admin/user_detail.html",
        managed_user=user,
        assignments=assignments,
        current_admin=_current_platform_administrator(),
    )


@admin_bp.route(
    "/users/<int:user_id>/suspend",
    methods=["POST"],
)
@admin_required
def suspend_user(user_id):
    """Suspend a user account without deleting its data."""
    current_admin = _current_platform_administrator()
    user = User.query.get_or_404(user_id)

    if current_admin is None:
        abort(403)

    if user.id == current_admin.id:
        flash(
            "You cannot suspend the account you are currently using "
            "for Platform Administration.",
            "danger",
        )
        return redirect(url_for("admin.user_detail", user_id=user.id))

    if user.account_status == SUSPENDED_ACCOUNT_STATUS:
        flash(
            f'"{user.full_name}" is already suspended.',
            "info",
        )
        return redirect(url_for("admin.user_detail", user_id=user.id))

    user.account_status = SUSPENDED_ACCOUNT_STATUS
    db.session.commit()

    flash(
        f'Suspended account for "{user.full_name}".',
        "success",
    )

    return redirect(url_for("admin.user_detail", user_id=user.id))


@admin_bp.route(
    "/users/<int:user_id>/reactivate",
    methods=["POST"],
)
@admin_required
def reactivate_user(user_id):
    """Reactivate a previously suspended DSA account."""
    user = User.query.get_or_404(user_id)

    if user.account_status == ACTIVE_ACCOUNT_STATUS:
        flash(
            f'"{user.full_name}" is already active.',
            "info",
        )
        return redirect(url_for("admin.user_detail", user_id=user.id))

    user.account_status = ACTIVE_ACCOUNT_STATUS
    db.session.commit()

    flash(
        f'Reactivated account for "{user.full_name}".',
        "success",
    )

    return redirect(url_for("admin.user_detail", user_id=user.id))

@admin_bp.route(
    "/role-assignments/<int:assignment_id>/revoke",
    methods=["POST"],
)
@admin_required
def revoke_role_assignment(assignment_id):
    """
    Revoke one privileged role assignment without suspending the user account.

    The currently signed-in Platform Administrator cannot revoke their own
    active Platform Administrator assignment from this interface. Other role
    assignments belonging to that same user may still be revoked.
    """
    current_admin = _current_platform_administrator()
    assignment = UserRoleAssignment.query.get_or_404(assignment_id)

    if current_admin is None:
        abort(403)

    if assignment.status != APPROVED_ASSIGNMENT_STATUS:
        flash(
            "Only an approved role assignment can be revoked.",
            "warning",
        )
        return redirect(
            url_for(
                "admin.user_detail",
                user_id=assignment.user_id,
            )
        )

    is_own_platform_admin_assignment = (
        assignment.user_id == current_admin.id
        and assignment.role is not None
        and assignment.role.name == "Platform Administrator"
    )

    if is_own_platform_admin_assignment:
        flash(
            "You cannot revoke your own active Platform Administration "
            "access from this interface.",
            "danger",
        )
        return redirect(
            url_for(
                "admin.user_detail",
                user_id=assignment.user_id,
            )
        )

    assignment.status = REVOKED_ASSIGNMENT_STATUS
    assignment.updated_at = _utcnow()

    db.session.commit()

    role_name = (
        assignment.role.name
        if assignment.role is not None
        else "Privileged role"
    )

    flash(
        f'Revoked "{role_name}" access for "{assignment.user.full_name}".',
        "success",
    )

    return redirect(
        url_for(
            "admin.user_detail",
            user_id=assignment.user_id,
        )
    )
    

@admin_bp.route("/guides")
@admin_required
def guides():
    """List SIWES Guide topics with administration controls."""
    topics = (
        GuideTopic.query
        .order_by(GuideTopic.order_num.asc())
        .all()
    )

    return render_template(
        "admin/guides.html",
        topics=topics,
    )


@admin_bp.route("/guides/new", methods=["GET", "POST"])
@admin_required
def new_guide():
    """Create a new platform SIWES guide topic."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = (
            request.form.get("slug", "")
            .strip()
            .lower()
            .replace(" ", "-")
        )
        category = request.form.get(
            "category",
            "General Guidance",
        ).strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()

        try:
            order_num = int(request.form.get("order_num", 0))
        except (TypeError, ValueError):
            order_num = 0

        icon = request.form.get("icon", "book-open").strip()

        topic = GuideTopic(
            slug=slug,
            title=title,
            category=category,
            summary=summary,
            content=content,
            order_num=order_num,
            icon=icon,
            is_published=True,
        )

        db.session.add(topic)
        db.session.commit()

        flash(
            f'Guide topic "{title}" created successfully.',
            "success",
        )

        return redirect(url_for("admin.guides"))

    return render_template(
        "admin/guide_form.html",
        topic=None,
    )


@admin_bp.route(
    "/guides/edit/<int:topic_id>",
    methods=["GET", "POST"],
)
@admin_required
def edit_guide(topic_id):
    """Edit an existing platform SIWES guide topic."""
    topic = GuideTopic.query.get_or_404(topic_id)

    if request.method == "POST":
        topic.title = request.form.get("title", "").strip()
        topic.slug = (
            request.form.get("slug", "")
            .strip()
            .lower()
            .replace(" ", "-")
        )
        topic.category = request.form.get(
            "category",
            topic.category,
        ).strip()
        topic.summary = request.form.get("summary", "").strip()
        topic.content = request.form.get("content", "").strip()

        try:
            topic.order_num = int(
                request.form.get(
                    "order_num",
                    topic.order_num,
                )
            )
        except (TypeError, ValueError):
            pass

        topic.icon = request.form.get(
            "icon",
            topic.icon,
        ).strip()

        topic.is_published = (
            request.form.get("is_published") == "on"
        )

        db.session.commit()

        flash(
            f'Updated guide topic "{topic.title}".',
            "success",
        )

        return redirect(url_for("admin.guides"))

    return render_template(
        "admin/guide_form.html",
        topic=topic,
    )