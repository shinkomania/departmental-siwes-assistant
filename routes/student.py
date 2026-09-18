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
    jsonify,
)

from models.db import db
from models.user import User
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication
from models.academic import Institution, AcademicUnit, Department, Programme
from models.directory_request import DirectoryRequest


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


def _parse_positive_int(value):
    """Safely convert a submitted identifier to a positive integer."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


@student_bp.route("/academic/institutions")
def academic_institutions():
    """
    Return active institutions available in DSA's controlled directory.

    Suspended, inactive, and rejected directory records are not exposed
    through the student academic-selection workflow.
    """
    institutions = (
        Institution.query
        .filter(
            Institution.is_active.is_(True),
            Institution.directory_status == "Verified",
        )
        .order_by(Institution.name.asc())
        .all()
    )

    return jsonify(
        [
            {
                "id": institution.id,
                "name": institution.name,
                "type": institution.institution_type,
                "city": institution.city,
                "state": institution.state,
                "directory_status": institution.directory_status,
            }
            for institution in institutions
        ]
    )


@student_bp.route("/academic/institutions/<int:institution_id>/units")
def academic_units(institution_id):
    """Return active academic units belonging to one institution."""
    institution = db.session.get(Institution, institution_id)

    if (
        not institution
        or not institution.is_active
        or institution.directory_status
        != "Verified"
    ):
        return jsonify([])

    units = (
        AcademicUnit.query
        .filter_by(
            institution_id=institution.id,
            is_active=True,
        )
        .order_by(AcademicUnit.name.asc())
        .all()
    )

    return jsonify(
        [
            {
                "id": unit.id,
                "name": unit.name,
                "type": unit.unit_type,
            }
            for unit in units
        ]
    )


@student_bp.route("/academic/units/<int:unit_id>/departments")
def academic_departments(unit_id):
    """Return active departments belonging to one academic unit."""
    unit = db.session.get(AcademicUnit, unit_id)

    if (
        not unit
        or not unit.is_active
        or not unit.institution
        or not unit.institution.is_active
        or unit.institution.directory_status
        != "Verified"
    ):
        return jsonify([])

    departments = (
        Department.query
        .filter_by(
            academic_unit_id=unit.id,
            is_active=True,
        )
        .order_by(Department.name.asc())
        .all()
    )

    return jsonify(
        [
            {
                "id": department.id,
                "name": department.name,
            }
            for department in departments
        ]
    )


@student_bp.route("/academic/departments/<int:department_id>/programmes")
def academic_programmes(department_id):
    """Return active programmes belonging to one department."""
    department = db.session.get(Department, department_id)

    if (
        not department
        or not department.is_active
        or not department.academic_unit
        or not department.academic_unit.is_active
        or not department.academic_unit.institution
        or not department.academic_unit.institution.is_active
        or department.academic_unit.institution.directory_status
        != "Verified"
    ):
        return jsonify([])

    programmes = (
        Programme.query
        .filter_by(
            department_id=department.id,
            is_active=True,
        )
        .order_by(Programme.name.asc())
        .all()
    )

    return jsonify(
        [
            {
                "id": programme.id,
                "name": programme.name,
                "award": programme.award,
                "duration_years": programme.duration_years,
                "siwes_status": (
                    programme.siwes_configuration.siwes_status
                    if programme.siwes_configuration
                    else "Pending Verification"
                ),
            }
            for programme in programmes
        ]
    )


@student_bp.route("/academic/directory-request", methods=["POST"])
def submit_directory_request():
    """
    Submit a missing institution or programme for Platform Admin review.

    Submission never creates or verifies authoritative academic directory
    records automatically.
    """
    user = _require_authenticated_user()

    if not user:
        flash(
            "Please sign in to submit an academic directory request.",
            "warning",
        )
        return redirect(
            url_for(
                "auth.login",
                next=url_for("student.profile"),
            )
        )

    request_type = request.form.get("request_type", "").strip()

    if request_type not in DirectoryRequest.REQUEST_TYPE_CHOICES:
        flash(
            "Please choose a valid academic directory request type.",
            "danger",
        )
        return redirect(url_for("student.profile"))

    institution_id = _parse_positive_int(
        request.form.get("institution_id")
    )

    institution_name = request.form.get(
        "institution_name",
        "",
    ).strip()

    institution_type = request.form.get(
        "institution_type",
        "",
    ).strip()

    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()

    official_website = request.form.get(
        "official_website",
        "",
    ).strip()

    academic_unit_name = request.form.get(
        "academic_unit_name",
        "",
    ).strip()

    academic_unit_type = request.form.get(
        "academic_unit_type",
        "",
    ).strip()

    department_name = request.form.get(
        "department_name",
        "",
    ).strip()

    programme_name = request.form.get(
        "programme_name",
        "",
    ).strip()

    award = request.form.get("award", "").strip()

    evidence_reference = request.form.get(
        "evidence_reference",
        "",
    ).strip()

    requester_notes = request.form.get(
        "requester_notes",
        "",
    ).strip()

    selected_institution = None

    if request_type == DirectoryRequest.TYPE_INSTITUTION:
        if not institution_name:
            flash(
                "Please provide the institution name.",
                "danger",
            )
            return redirect(url_for("student.profile"))

        # An institution request represents a school that is not yet
        # available in the controlled directory.
        institution_id = None

    elif request_type == DirectoryRequest.TYPE_PROGRAMME:
        if not institution_id:
            flash(
                "Please select the institution for the missing programme.",
                "danger",
            )
            return redirect(url_for("student.profile"))

        selected_institution = db.session.get(
            Institution,
            institution_id,
        )

        if (
            not selected_institution
            or not selected_institution.is_active
            or selected_institution.directory_status != "Verified"
        ):
            flash(
                "Please select a verified institution from the directory.",
                "danger",
            )
            return redirect(url_for("student.profile"))

        if not programme_name:
            flash(
                "Please provide the missing programme name.",
                "danger",
            )
            return redirect(url_for("student.profile"))

        # Directory data is authoritative for an existing institution.
        institution_name = selected_institution.name
        institution_type = selected_institution.institution_type or ""
        city = selected_institution.city or ""
        state = selected_institution.state or ""
        official_website = selected_institution.official_website or ""

    open_statuses = [
        DirectoryRequest.STATUS_SUBMITTED,
        DirectoryRequest.STATUS_UNDER_REVIEW,
        DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
    ]

    duplicate_query = DirectoryRequest.query.filter(
        DirectoryRequest.user_id == user.id,
        DirectoryRequest.request_type == request_type,
        DirectoryRequest.status.in_(open_statuses),
    )

    if request_type == DirectoryRequest.TYPE_INSTITUTION:
        duplicate_query = duplicate_query.filter(
            db.func.lower(DirectoryRequest.institution_name)
            == institution_name.lower()
        )
    else:
        duplicate_query = duplicate_query.filter(
            DirectoryRequest.institution_id == institution_id,
            db.func.lower(DirectoryRequest.programme_name)
            == programme_name.lower(),
        )

    if duplicate_query.first():
        flash(
            "You already have an open request for this academic directory item.",
            "info",
        )
        return redirect(url_for("student.profile"))

    directory_request = DirectoryRequest(
        user_id=user.id,
        request_type=request_type,
        institution_id=institution_id,
        institution_name=institution_name,
        institution_type=institution_type or None,
        city=city or None,
        state=state or None,
        official_website=official_website or None,
        academic_unit_name=academic_unit_name or None,
        academic_unit_type=academic_unit_type or None,
        department_name=department_name or None,
        programme_name=programme_name or None,
        award=award or None,
        evidence_reference=evidence_reference or None,
        requester_notes=requester_notes or None,
    )

    db.session.add(directory_request)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

        flash(
            "We could not submit your directory request. Please try again.",
            "danger",
        )
        return redirect(url_for("student.profile"))

    flash(
        "Your academic directory request has been submitted for review.",
        "success",
    )

    return redirect(url_for("student.profile"))


@student_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """
    View, create, or update the authenticated user's own student profile.

    Structured academic identity follows:

        Institution -> Academic Unit -> Department -> Programme

    Legacy academic text fields remain synchronized temporarily so older
    dashboard/template code continues to work during the Phase 4 migration.
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

    def render_profile():
        selected_institution_id = None
        selected_academic_unit_id = None
        selected_department_id = None
        selected_programme_id = None

        if student and student.programme:
            selected_programme_id = student.programme.id

            department = student.programme.department
            if department:
                selected_department_id = department.id

                academic_unit = department.academic_unit
                if academic_unit:
                    selected_academic_unit_id = academic_unit.id

                    institution = academic_unit.institution
                    if institution:
                        selected_institution_id = institution.id

        return render_template(
            "profile.html",
            student=student,
            interests=AREAS_OF_INTEREST,
            org_types=ORGANIZATION_TYPES,
            states=NIGERIAN_STATES,
            selected_institution_id=selected_institution_id,
            selected_academic_unit_id=selected_academic_unit_id,
            selected_department_id=selected_department_id,
            selected_programme_id=selected_programme_id,
        )

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        matric_no = request.form.get("matric_no", "").strip()

        preferred_state = request.form.get(
            "preferred_state",
            "",
        ).strip()

        preferred_city = request.form.get(
            "preferred_city",
            "",
        ).strip()

        area_of_interest = request.form.get(
            "area_of_interest",
            "",
        ).strip()

        skills = request.form.get("skills", "").strip()

        preferred_org_type = request.form.get(
            "preferred_org_type",
            "",
        ).strip()

        bio = request.form.get("bio", "").strip()

        level = request.form.get("level", "").strip()
        siwes_session = request.form.get(
            "siwes_session",
            "",
        ).strip()

        institution_id = _parse_positive_int(
            request.form.get("institution_id")
        )

        academic_unit_id = _parse_positive_int(
            request.form.get("academic_unit_id")
        )

        department_id = _parse_positive_int(
            request.form.get("department_id")
        )

        programme_id = _parse_positive_int(
            request.form.get("programme_id")
        )

        submitted_academic_ids = any(
            (
                institution_id,
                academic_unit_id,
                department_id,
                programme_id,
            )
        )

        if (
            not full_name
            or not matric_no
            or not preferred_state
            or not area_of_interest
        ):
            flash(
                "Please fill in all required profile fields.",
                "danger",
            )
            return render_profile()

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
            return render_profile()

        selected_programme = None
        selected_department = None
        selected_unit = None
        selected_institution = None

        if submitted_academic_ids:
            if not all(
                (
                    institution_id,
                    academic_unit_id,
                    department_id,
                    programme_id,
                )
            ):
                flash(
                    "Please complete your institution, academic unit, "
                    "department, and programme selection.",
                    "danger",
                )
                return render_profile()

            selected_institution = db.session.get(
                Institution,
                institution_id,
            )

            selected_unit = db.session.get(
                AcademicUnit,
                academic_unit_id,
            )

            selected_department = db.session.get(
                Department,
                department_id,
            )

            selected_programme = db.session.get(
                Programme,
                programme_id,
            )

            valid_hierarchy = (
                selected_institution is not None
                and selected_unit is not None
                and selected_department is not None
                and selected_programme is not None
                and selected_institution.is_active
                and selected_unit.is_active
                and selected_department.is_active
                and selected_programme.is_active
                and selected_institution.directory_status == "Verified"
                and selected_unit.institution_id
                == selected_institution.id
                and selected_department.academic_unit_id
                == selected_unit.id
                and selected_programme.department_id
                == selected_department.id
            )

            if not valid_hierarchy:
                flash(
                    "The selected academic programme does not match the "
                    "institution hierarchy. Please select your academic "
                    "details again.",
                    "danger",
                )
                return render_profile()

        if selected_programme:
            # Structured hierarchy is authoritative.
            programme_value = selected_programme.id
            department_value = selected_department.name
            faculty_value = selected_unit.name
            university_value = selected_institution.name

        elif student:
            # Transitional fallback for an existing legacy profile.
            programme_value = student.programme_id
            department_value = student.department
            faculty_value = student.faculty
            university_value = student.university

        else:
            # Current legacy form fallback until the controlled academic
            # directory UI is activated.
            department_value = request.form.get(
                "department",
                "",
            ).strip()

            faculty_value = request.form.get(
                "faculty",
                "",
            ).strip()

            university_value = request.form.get(
                "university",
                "",
            ).strip()

            programme_value = None

            if (
                not department_value
                or not faculty_value
                or not university_value
            ):
                flash(
                    "Please provide your academic institution details.",
                    "danger",
                )
                return render_profile()

        if student:
            student.full_name = full_name
            student.matric_no = matric_no

            student.programme_id = programme_value
            student.level = level or student.level
            student.siwes_session = (
                siwes_session or student.siwes_session
            )

            # Legacy compatibility fields are derived from the structured
            # hierarchy whenever a programme has been selected.
            student.department = department_value
            student.faculty = faculty_value
            student.university = university_value

            student.preferred_state = preferred_state
            student.preferred_city = preferred_city
            student.area_of_interest = area_of_interest
            student.skills = skills
            student.preferred_org_type = preferred_org_type
            student.bio = bio

            success_message = "Student profile updated successfully!"

        else:
            student = StudentProfile(
                user_id=user.id,
                full_name=full_name,
                matric_no=matric_no,
                programme_id=programme_value,
                level=level or None,
                siwes_session=siwes_session or None,
                department=department_value,
                faculty=faculty_value,
                university=university_value,
                preferred_state=preferred_state,
                preferred_city=preferred_city,
                area_of_interest=area_of_interest,
                skills=skills,
                preferred_org_type=preferred_org_type,
                bio=bio,
            )

            db.session.add(student)

            success_message = "Student profile created successfully!"

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

            flash(
                "We could not save your student profile. Please try again.",
                "danger",
            )

            return render_profile()

        flash(success_message, "success")

        # Remove any legacy student-session authority.
        session.pop("student_id", None)

        return redirect(url_for("student.dashboard"))

    return render_profile()

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


