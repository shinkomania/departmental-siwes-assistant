"""
Student Routes Blueprint
------------------------
Handles authenticated student profile management and the student dashboard.

Student data ownership is based on:

    authenticated User -> StudentProfile

Legacy session['student_id'] is no longer trusted as an authentication
or authorization mechanism.
"""

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
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication


student_bp = Blueprint("student", __name__)


# Transitional placement-interest options.
# These will later be replaced by programme/field-aware configuration.
AREAS_OF_INTEREST = [
    "Software Development",
    "Artificial Intelligence",
    "Machine Learning",
    "Web Development",
    "Mobile Development",
    "Networking & Telecommunications",
    "Cybersecurity",
    "Embedded Systems & IoT",
    "Computer Hardware & Maintenance",
    "Data Science & Analytics",
    "Cloud Computing & DevOps",
    "Engineering",
    "Science & Laboratory",
    "Business & Administration",
    "Finance & Accounting",
    "Agriculture",
    "Health & Life Sciences",
    "Media & Communication",
    "Research",
    "Other",
]


ORGANIZATION_TYPES = [
    "Technology company",
    "Software company",
    "Telecom company",
    "Bank/Fintech",
    "Government organization",
    "Engineering company",
    "Research organization",
    "Healthcare organization",
    "Manufacturing company",
    "Agricultural organization",
    "Consulting company",
    "NGO / Non-profit",
    "Startup",
    "Other",
]


NIGERIAN_STATES = [
    "Abia",
    "Adamawa",
    "Akwa Ibom",
    "Anambra",
    "Bauchi",
    "Bayelsa",
    "Benue",
    "Borno",
    "Cross River",
    "Delta",
    "Ebonyi",
    "Edo",
    "Ekiti",
    "Enugu",
    "FCT Abuja",
    "Gombe",
    "Imo",
    "Jigawa",
    "Kaduna",
    "Kano",
    "Katsina",
    "Kebbi",
    "Kogi",
    "Kwara",
    "Lagos",
    "Nasarawa",
    "Niger",
    "Ogun",
    "Ondo",
    "Osun",
    "Oyo",
    "Plateau",
    "Rivers",
    "Sokoto",
    "Taraba",
    "Yobe",
    "Zamfara",
]


def _current_user():
    """
    Return the currently authenticated active User.

    Authentication authority comes only from session['user_id'].
    """
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if not user:
        return None

    if user.account_status != "Active":
        return None

    return user


def _current_student():
    """
    Return the StudentProfile belonging to the authenticated User.

    A StudentProfile owned by another User can never be selected through
    session values, query parameters, matric numbers, or URLs.
    """
    user = _current_user()

    if not user:
        return None

    return StudentProfile.query.filter_by(user_id=user.id).first()


def _require_authenticated_user():
    """
    Return the authenticated User or None.

    Route functions handle the redirect themselves so the helper stays simple.
    """
    return _current_user()


@student_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """
    View, create, or update the authenticated user's own student profile.

    Legacy profile lookup by matric number has intentionally been removed.
    """
    user = _require_authenticated_user()

    if not user:
        flash(
            "Please sign in to create or manage your student profile.",
            "warning",
        )
        return redirect(
            url_for(
                "auth.login",
                next=request.path,
            )
        )

    student = StudentProfile.query.filter_by(user_id=user.id).first()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        matric_no = request.form.get("matric_no", "").strip()
        department = request.form.get("department", "").strip()
        faculty = request.form.get("faculty", "").strip()
        university = request.form.get("university", "").strip()
        preferred_state = request.form.get("preferred_state", "").strip()
        preferred_city = request.form.get("preferred_city", "").strip()
        area_of_interest = request.form.get("area_of_interest", "").strip()
        skills = request.form.get("skills", "").strip()
        preferred_org_type = request.form.get(
            "preferred_org_type",
            "",
        ).strip()
        bio = request.form.get("bio", "").strip()

        if (
            not full_name
            or not matric_no
            or not university
            or not preferred_state
            or not area_of_interest
        ):
            flash(
                "Please fill in all required profile fields.",
                "danger",
            )
            return render_template(
                "profile.html",
                student=student,
                interests=AREAS_OF_INTEREST,
                org_types=ORGANIZATION_TYPES,
                states=NIGERIAN_STATES,
            )

        existing_matric = StudentProfile.query.filter_by(
            matric_no=matric_no
        ).first()

        if existing_matric and (
            not student or existing_matric.id != student.id
        ):
            flash(
                "That matriculation number is already registered to "
                "another student profile.",
                "warning",
            )
            return render_template(
                "profile.html",
                student=student,
                interests=AREAS_OF_INTEREST,
                org_types=ORGANIZATION_TYPES,
                states=NIGERIAN_STATES,
            )

        if student:
            student.full_name = full_name
            student.matric_no = matric_no
            student.department = department
            student.faculty = faculty
            student.university = university
            student.preferred_state = preferred_state
            student.preferred_city = preferred_city
            student.area_of_interest = area_of_interest
            student.skills = skills
            student.preferred_org_type = preferred_org_type
            student.bio = bio

            flash(
                "Student profile updated successfully!",
                "success",
            )

        else:
            student = StudentProfile(
                user_id=user.id,
                full_name=full_name,
                matric_no=matric_no,
                department=department,
                faculty=faculty,
                university=university,
                preferred_state=preferred_state,
                preferred_city=preferred_city,
                area_of_interest=area_of_interest,
                skills=skills,
                preferred_org_type=preferred_org_type,
                bio=bio,
            )

            db.session.add(student)

            flash(
                "Student profile created successfully!",
                "success",
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

            flash(
                "We could not save your student profile. Please try again.",
                "danger",
            )

            return render_template(
                "profile.html",
                student=student,
                interests=AREAS_OF_INTEREST,
                org_types=ORGANIZATION_TYPES,
                states=NIGERIAN_STATES,
            )

        # Remove any legacy student-session authority.
        session.pop("student_id", None)

        return redirect(url_for("student.dashboard"))

    return render_template(
        "profile.html",
        student=student,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES,
        states=NIGERIAN_STATES,
    )


@student_bp.route("/dashboard")
def dashboard():
    """
    Student dashboard for the authenticated user's own StudentProfile.
    """
    user = _require_authenticated_user()

    if not user:
        flash(
            "Please sign in to access your student dashboard.",
            "warning",
        )
        return redirect(
            url_for(
                "auth.login",
                next=request.path,
            )
        )

    student = StudentProfile.query.filter_by(
        user_id=user.id
    ).first()

    if not student:
        flash(
            "Please complete your student profile to access the "
            "personalized SIWES dashboard.",
            "info",
        )
        return redirect(url_for("student.profile"))

    saved_entries = (
        SavedOrganization.query.filter_by(
            student_id=student.id
        )
        .order_by(SavedOrganization.saved_at.desc())
        .all()
    )

    applications = (
        PlacementApplication.query.filter_by(
            student_id=student.id
        )
        .order_by(PlacementApplication.updated_at.desc())
        .all()
    )

    status_counts = {
        "Interested": 0,
        "Contacted": 0,
        "Application Submitted": 0,
        "Interview": 0,
        "Accepted": 0,
        "Rejected": 0,
    }

    for application in applications:
        if application.status in status_counts:
            status_counts[application.status] += 1

    return render_template(
        "dashboard.html",
        student=student,
        saved_entries=saved_entries,
        applications=applications,
        status_counts=status_counts,
        total_saved=len(saved_entries),
        total_applied=len(applications),
        status_choices=PlacementApplication.STATUS_CHOICES,
    )


