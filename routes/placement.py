"""
Placement Routes Blueprint
--------------------------
Handles SIWES placement search, search results, organization details,
bookmarking, application tracking, and student organization submissions.

Personalized placement data is always resolved through the authenticated
User -> StudentProfile relationship.
"""

from datetime import datetime, date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from models.db import db
from models.user import User
from models.organization import Organization
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication
from services.placement_search import PlacementSearchService
from routes.student import (
    AREAS_OF_INTEREST,
    ORGANIZATION_TYPES,
    NIGERIAN_STATES,
)


placement_bp = Blueprint("placement", __name__)

search_service = PlacementSearchService()

def _current_user():
    """
    Return the authenticated active User.

    Authentication authority is session['user_id'] only.
    Inactive, deleted, or unauthenticated users return None.
    """
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if user is None:
        return None

    if user.account_status != "Active":
        return None

    return user

def _current_student():
    """
    Return the StudentProfile owned by the authenticated active User.

    Authentication authority is session['user_id'] only.
    session['student_id'] is intentionally ignored.

    If the User no longer exists or their account is not Active,
    no StudentProfile is returned.
    """
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if user is None:
        return None

    if user.account_status != "Active":
        return None

    return StudentProfile.query.filter_by(
        user_id=user.id
    ).first()


def _require_student_profile():
    """
    Resolve the authenticated active user's StudentProfile.

    Returns None when the user is logged out, inactive,
    missing, or has not created a profile.
    """
    return _current_student()


@placement_bp.route("/placement")
def search_form():
    """
    Placement search form.

    Placement browsing remains public. If an authenticated user has a
    StudentProfile, their preferences are used only to pre-populate filters.
    """
    student = _current_student()

    default_state = student.preferred_state if student else ""
    default_city = student.preferred_city if student else ""
    default_interest = student.area_of_interest if student else ""
    default_org_type = student.preferred_org_type if student else ""

    return render_template(
        "placement.html",
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES,
        default_state=default_state,
        default_city=default_city,
        default_interest=default_interest,
        default_org_type=default_org_type,
    )


@placement_bp.route("/placement/results")
def search_results():
    """
    Execute placement search and display result cards.

    Public users may search. Bookmark state is shown only for the
    authenticated user's own StudentProfile.
    """
    state = request.args.get("state", "").strip()
    city = request.args.get("city", "").strip()
    interest = request.args.get("interest", "").strip()
    org_type = request.args.get("org_type", "").strip()
    keywords = request.args.get("keywords", "").strip()

    search_data = search_service.search(
        state=state,
        city=city,
        interest=interest,
        org_type=org_type,
        keywords=keywords,
    )

    student = _current_student()
    saved_org_ids = set()

    if student:
        saved_entries = SavedOrganization.query.filter_by(
            student_id=student.id
        ).all()

        saved_org_ids = {
            entry.organization_id
            for entry in saved_entries
        }

    return render_template(
        "results.html",
        results=search_data["database_results"],
        web_results=search_data["web_results"],
        live_search_status=search_data["live_search_status"],
        total_count=search_data["total_count"],
        query_params=search_data["query_params"],
        saved_org_ids=saved_org_ids,
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES,
    )


@placement_bp.route("/placement/<int:org_id>")
def organization_detail(org_id):
    """
    Detailed view for a specific organization.

    Organization browsing remains public.
    """
    org = Organization.query.get_or_404(org_id)

    student = _current_student()
    is_saved = False
    application = None

    if student:
        is_saved = (
            SavedOrganization.query.filter_by(
                student_id=student.id,
                organization_id=org.id,
            ).first()
            is not None
        )

        application = PlacementApplication.query.filter_by(
            student_id=student.id,
            organization_id=org.id,
        ).first()

    return render_template(
        "organization.html",
        org=org,
        is_saved=is_saved,
        application=application,
        status_choices=PlacementApplication.STATUS_CHOICES,
    )


@placement_bp.route(
    "/placement/save/<int:org_id>",
    methods=["POST"],
)
def toggle_save(org_id):
    """
    Save or remove an organization from the authenticated student's bookmarks.
    """
    if not session.get("user_id"):
        flash(
            "Please sign in before saving organizations.",
            "warning",
        )
        return redirect(
            url_for(
                "auth.login",
                next=url_for(
                    "placement.organization_detail",
                    org_id=org_id,
                ),
            )
        )

    student = _require_student_profile()

    if not student:
        flash(
            "Please complete your student profile before saving organizations.",
            "warning",
        )
        return redirect(url_for("student.profile"))

    org = Organization.query.get_or_404(org_id)

    existing = SavedOrganization.query.filter_by(
        student_id=student.id,
        organization_id=org.id,
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()

        flash(
            f"Removed {org.name} from your saved organizations.",
            "info",
        )

    else:
        new_save = SavedOrganization(
            student_id=student.id,
            organization_id=org.id,
        )

        db.session.add(new_save)
        db.session.commit()

        flash(
            f"Saved {org.name} to your dashboard!",
            "success",
        )

    redirect_to = (
        request.referrer
        or url_for(
            "placement.organization_detail",
            org_id=org.id,
        )
    )

    return redirect(redirect_to)


@placement_bp.route(
    "/placement/track/<int:org_id>",
    methods=["POST"],
)
def track_application(org_id):
    """
    Create or update a placement application belonging to the authenticated
    student's own profile.
    """
    if not session.get("user_id"):
        flash(
            "Please sign in before tracking placement applications.",
            "warning",
        )
        return redirect(
            url_for(
                "auth.login",
                next=url_for(
                    "placement.organization_detail",
                    org_id=org_id,
                ),
            )
        )

    student = _require_student_profile()

    if not student:
        flash(
            "Please complete your student profile before tracking "
            "placement applications.",
            "warning",
        )
        return redirect(url_for("student.profile"))

    org = Organization.query.get_or_404(org_id)

    status = request.form.get(
        "status",
        "Interested",
    ).strip()

    notes = request.form.get(
        "notes",
        "",
    ).strip()

    applied_date_str = request.form.get(
        "applied_date",
        "",
    ).strip()

    if status not in PlacementApplication.STATUS_CHOICES:
        status = "Interested"

    applied_date = None

    if applied_date_str:
        try:
            applied_date = datetime.strptime(
                applied_date_str,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            applied_date = date.today()

    application = PlacementApplication.query.filter_by(
        student_id=student.id,
        organization_id=org.id,
    ).first()

    if application:
        application.status = status
        application.notes = notes

        if applied_date:
            application.applied_date = applied_date

        flash(
            f"Application status for {org.name} updated to: {status}",
            "success",
        )

    else:
        application = PlacementApplication(
            student_id=student.id,
            organization_id=org.id,
            status=status,
            notes=notes,
            applied_date=applied_date or date.today(),
        )

        db.session.add(application)

        flash(
            f'Added {org.name} to your application tracker as "{status}"!',
            "success",
        )

    db.session.commit()

    return redirect(url_for("student.dashboard"))


@placement_bp.route(
    "/placement/submit-org",
    methods=["GET", "POST"],
)
def submit_organization():
    """
    Accept a community suggestion for a potential SIWES organization.

    Only authenticated, active DSA users may contribute suggestions.
    A StudentProfile is intentionally not required because contributors
    may include students, staff, coordinators, alumni, employers, and
    other community users.

    Community contributions enter DSA as pending review. Submission does
    not mean that DSA has verified the organization, confirmed that the
    organization currently accepts SIWES students, or confirmed suitability
    for any particular programme.
    """
    user = _current_user()

    if user is None:
        flash(
            "Please sign in before suggesting a SIWES organization.",
            "warning",
        )
        return redirect(
            url_for(
                "auth.login",
                next=request.url,
            )
        )

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        address = request.form.get("address", "").strip()
        state = request.form.get("state", "").strip()
        city = request.form.get("city", "").strip()
        industry = request.form.get("industry", "").strip()

        relevance_areas = request.form.get(
            "relevance_areas",
            "",
        ).strip()

        website = request.form.get(
            "website",
            "",
        ).strip()

        contact_email = request.form.get(
            "contact_email",
            "",
        ).strip()

        contact_phone = request.form.get(
            "contact_phone",
            "",
        ).strip()

        why_relevant = request.form.get(
            "why_relevant",
            "",
        ).strip()

        if not name or not state or not city or not industry:
            flash(
                "Please provide organization name, state, city, and industry.",
                "danger",
            )
            return render_template(
                "submit_org.html",
                states=NIGERIAN_STATES,
                interests=AREAS_OF_INTEREST,
                org_types=ORGANIZATION_TYPES,
            )

        contribution_note = (
            why_relevant
            or (
                "Suggested by a DSA community contributor as a potential "
                f"SIWES organization relevant to {relevance_areas or industry}."
            )
        )

        new_org = Organization(
            name=name,
            description=(
                description
                or f"Community-suggested organization in {city}, {state}."
            ),
            address=address,
            state=state,
            city=city,
            industry=industry,
            relevance_areas=relevance_areas or industry,
            website=website,
            contact_email=contact_email,
            contact_phone=contact_phone,

            # Provenance and review state
            source_type="Community Contribution",
            source_name="DSA Community Contribution",
            provenance_notes=contribution_note,
            review_status="Pending",

            # A community suggestion is not automatically an approved
            # directory listing or evidence of current SIWES intake.
            listing_status="Unknown",
            acceptance_status="Unknown",
            is_active=False,

            # Temporary compatibility values for legacy non-null columns.
            # New UI and application logic must use the provenance fields above.
            verification_status="Pending Review",
            source="Community Contribution",
            why_relevant=contribution_note,
        )

        db.session.add(new_org)
        db.session.commit()

        flash(
            (
                f'Thank you! "{name}" has been submitted for review. '
                "Its submission does not confirm current SIWES intake "
                "or programme suitability."
            ),
            "success",
        )

        return redirect(
    url_for("placement.search_form")

        )

    return render_template(
        "submit_org.html",
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES,
    )