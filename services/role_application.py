"""
Administrative Role Application Submission Service
--------------------------------------------------
Creates privileged DSA role applications only after validating the applicant,
requested role, academic scope, verification method, and duplicate-open-request
rules.

An application never grants access. Access is created separately through the
role approval workflow.
"""

from models.db import db
from models.user import User
from models.access import Role
from models.academic import Institution, Department, Programme
from models.role_application import RoleApplication


ACTIVE_ACCOUNT_STATUS = "Active"

SUPPORTED_REQUEST_ROLE_SLUGS = {
    "primary_institution_administrator",
    "institution_siwes_officer",
    "departmental_siwes_coordinator",
}

OPEN_APPLICATION_STATUSES = {
    RoleApplication.STATUS_SUBMITTED,
    RoleApplication.STATUS_PENDING_VERIFICATION,
    RoleApplication.STATUS_UNDER_REVIEW,
    RoleApplication.STATUS_MORE_INFO_REQUIRED,
}


class RoleApplicationSubmissionError(ValueError):
    """Raised when a privileged-role application cannot be submitted."""


def _clean_optional(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _require_active_applicant(user):
    if user is None or getattr(user, "id", None) is None:
        raise RoleApplicationSubmissionError("Applicant user is required.")

    if getattr(user, "account_status", None) != ACTIVE_ACCOUNT_STATUS:
        raise RoleApplicationSubmissionError(
            "Applicant user account is not active."
        )


def _get_supported_role(requested_role):
    if requested_role is None:
        raise RoleApplicationSubmissionError("Requested role is required.")

    if isinstance(requested_role, str):
        role = Role.query.filter_by(slug=requested_role.strip()).first()
    elif isinstance(requested_role, int):
        role = db.session.get(Role, requested_role)
    else:
        role = requested_role

    if role is None or getattr(role, "id", None) is None or not role.is_active:
        raise RoleApplicationSubmissionError(
            "Requested role does not exist or is inactive."
        )

    if role.slug not in SUPPORTED_REQUEST_ROLE_SLUGS:
        raise RoleApplicationSubmissionError(
            f"Role '{role.slug}' cannot be requested through this workflow."
        )

    return role


def _validate_scope(role, institution_id, department_id, programme_id):
    institution = db.session.get(Institution, institution_id)

    if institution is None or not institution.is_active:
        raise RoleApplicationSubmissionError(
            "Selected institution is invalid or inactive."
        )

    if role.slug in {
        "primary_institution_administrator",
        "institution_siwes_officer",
    }:
        if department_id is not None or programme_id is not None:
            raise RoleApplicationSubmissionError(
                f"Role '{role.slug}' must be scoped to an institution only."
            )
        return institution.id, None, None

    if department_id is None:
        raise RoleApplicationSubmissionError(
            "A Departmental SIWES Coordinator application must include a department."
        )

    department = db.session.get(Department, department_id)

    if (
        department is None
        or not department.is_active
        or department.academic_unit is None
        or not department.academic_unit.is_active
        or department.academic_unit.institution is None
        or not department.academic_unit.institution.is_active
    ):
        raise RoleApplicationSubmissionError(
            "Selected department is invalid or inactive."
        )

    if department.academic_unit.institution_id != institution.id:
        raise RoleApplicationSubmissionError(
            "Selected department does not belong to the selected institution."
        )

    if programme_id is not None:
        programme = db.session.get(Programme, programme_id)

        if programme is None or not programme.is_active:
            raise RoleApplicationSubmissionError(
                "Selected programme is invalid or inactive."
            )

        if programme.department_id != department.id:
            raise RoleApplicationSubmissionError(
                "Selected programme does not belong to the selected department."
            )

    return institution.id, department.id, programme_id


def _validate_verification_method(verification_method):
    verification_method = _clean_optional(verification_method)

    if verification_method is None:
        return None

    if verification_method not in RoleApplication.VERIFICATION_METHOD_CHOICES:
        raise RoleApplicationSubmissionError(
            "Selected verification method is not supported."
        )

    return verification_method


def _find_duplicate_open_application(
    applicant_id,
    role_id,
    institution_id,
    department_id,
    programme_id,
    academic_session,
):
    return RoleApplication.query.filter(
        RoleApplication.user_id == applicant_id,
        RoleApplication.requested_role_id == role_id,
        RoleApplication.institution_id == institution_id,
        RoleApplication.department_id == department_id,
        RoleApplication.programme_id == programme_id,
        RoleApplication.academic_session == academic_session,
        RoleApplication.status.in_(OPEN_APPLICATION_STATUSES),
    ).first()


def submit_role_application(
    applicant_user,
    requested_role,
    institution_id,
    official_position,
    *,
    department_id=None,
    programme_id=None,
    academic_session=None,
    institutional_email=None,
    phone=None,
    verification_method=None,
    evidence_reference=None,
    evidence_notes=None,
    evidence_file_reference=None,
    applicant_notes=None,
):
    """
    Validate and create a privileged administrative role application.

    Departmental coordinator scope:
    - department_id is required;
    - programme_id is optional;
    - when supplied, the programme must belong to the selected department.

    Returns:
        RoleApplication
    """
    _require_active_applicant(applicant_user)

    role = _get_supported_role(requested_role)

    official_position = _clean_optional(official_position)
    if official_position is None:
        raise RoleApplicationSubmissionError(
            "Official position is required."
        )

    academic_session = _clean_optional(academic_session)
    institutional_email = _clean_optional(institutional_email)
    phone = _clean_optional(phone)
    verification_method = _validate_verification_method(verification_method)
    evidence_reference = _clean_optional(evidence_reference)
    evidence_notes = _clean_optional(evidence_notes)
    evidence_file_reference = _clean_optional(evidence_file_reference)
    applicant_notes = _clean_optional(applicant_notes)

    institution_id, department_id, programme_id = _validate_scope(
        role,
        institution_id,
        department_id,
        programme_id,
    )

    duplicate = _find_duplicate_open_application(
        applicant_user.id,
        role.id,
        institution_id,
        department_id,
        programme_id,
        academic_session,
    )

    if duplicate is not None:
        raise RoleApplicationSubmissionError(
            "An open application already exists for this role, scope, and academic session."
        )

    application = RoleApplication(
        user_id=applicant_user.id,
        requested_role_id=role.id,
        institution_id=institution_id,
        department_id=department_id,
        programme_id=programme_id,
        academic_session=academic_session,
        official_position=official_position,
        institutional_email=institutional_email,
        phone=phone,
        verification_method=verification_method,
        evidence_reference=evidence_reference,
        evidence_notes=evidence_notes,
        evidence_file_reference=evidence_file_reference,
        applicant_notes=applicant_notes,
        status=RoleApplication.STATUS_SUBMITTED,
    )

    db.session.add(application)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return application
