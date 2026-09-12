"""
Administrative Role Approval Service
------------------------------------
Safely converts an approved administrative role application into a scoped
UserRoleAssignment.

Security rules:
- Applications must exist and still be reviewable.
- Applicant and reviewer accounts must be active.
- Only supported privileged roles can be approved through this workflow.
- Platform Administrator and Student roles cannot be requested here.
- Requested academic scope must be valid and internally consistent.
- Duplicate active assignments are not created.
- Approval and assignment creation happen in one database transaction.

Important:
This service validates the requested scope and materializes the assignment.
Route-level authorization for who is allowed to review each application will
be connected separately through the authorization service.
"""

from datetime import datetime

from models.db import db
from models.user import User
from models.access import UserRoleAssignment
from models.academic import Department, Programme
from models.role_application import RoleApplication


ACTIVE_ACCOUNT_STATUS = "Active"
APPROVED_ASSIGNMENT_STATUS = "Approved"

SUPPORTED_REQUEST_ROLE_SLUGS = {
    "primary_institution_administrator",
    "institution_siwes_officer",
    "departmental_siwes_coordinator",
}


class RoleApprovalError(ValueError):
    """Raised when an administrative role application cannot be approved."""


def _utcnow():
    return datetime.utcnow()


def _require_active_user(user, label):
    if user is None or getattr(user, "id", None) is None:
        raise RoleApprovalError(f"{label} user is required.")

    if getattr(user, "account_status", None) != ACTIVE_ACCOUNT_STATUS:
        raise RoleApprovalError(f"{label} user account is not active.")


def _validate_requested_scope(application):
    """
    Validate role-specific scope and academic hierarchy.

    Returns:
        (institution_id, department_id, programme_id)
    """
    if application.institution_id is None:
        raise RoleApprovalError("An institution is required for this role application.")

    role = application.requested_role

    if role is None or not role.is_active:
        raise RoleApprovalError("Requested role does not exist or is inactive.")

    role_slug = role.slug

    if role_slug not in SUPPORTED_REQUEST_ROLE_SLUGS:
        raise RoleApprovalError(
            f"Role '{role_slug}' cannot be approved through this workflow."
        )

    institution_id = application.institution_id
    department_id = application.department_id
    programme_id = application.programme_id

    if role_slug in {
        "primary_institution_administrator",
        "institution_siwes_officer",
    }:
        if department_id is not None or programme_id is not None:
            raise RoleApprovalError(
                f"Role '{role_slug}' must be scoped to an institution only."
            )

        return institution_id, None, None

    # Departmental coordinator must have a department.
    if department_id is None:
        raise RoleApprovalError(
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
        raise RoleApprovalError("Requested department is invalid or inactive.")

    actual_institution_id = department.academic_unit.institution_id

    if actual_institution_id != institution_id:
        raise RoleApprovalError(
            "Requested department does not belong to the selected institution."
        )

    if programme_id is not None:
        programme = db.session.get(Programme, programme_id)

        if programme is None or not programme.is_active:
            raise RoleApprovalError("Requested programme is invalid or inactive.")

        if programme.department_id != department_id:
            raise RoleApprovalError(
                "Requested programme does not belong to the selected department."
            )

    return institution_id, department_id, programme_id


def _find_existing_assignment(
    application,
    institution_id,
    department_id,
    programme_id,
):
    """
    Find an equivalent currently-approved assignment.

    Exact scope matching is intentional. A broader or narrower assignment is
    not silently treated as the same authorization grant.
    """
    return UserRoleAssignment.query.filter_by(
        user_id=application.user_id,
        role_id=application.requested_role_id,
        institution_id=institution_id,
        department_id=department_id,
        programme_id=programme_id,
        status=APPROVED_ASSIGNMENT_STATUS,
        academic_session=application.academic_session,
    ).first()


def approve_role_application(
    application,
    reviewer_user,
    reviewer_notes=None,
    expires_at=None,
):
    """
    Approve an administrative role application and create its scoped assignment.

    Returns:
        UserRoleAssignment

    Raises:
        RoleApprovalError on invalid state, user, role, scope, or duplicate grant.

    Notes:
    - This function does not decide whether the reviewer is authorized to review
      this application. Route/service authorization must check that before calling
      this function.
    - No commit is performed until all validation succeeds.
    """
    if application is None or getattr(application, "id", None) is None:
        raise RoleApprovalError("Role application is required.")

    if application.status not in {
        RoleApplication.STATUS_SUBMITTED,
        RoleApplication.STATUS_PENDING_VERIFICATION,
        RoleApplication.STATUS_UNDER_REVIEW,
        RoleApplication.STATUS_MORE_INFO_REQUIRED,
    }:
        raise RoleApprovalError(
            f"Application cannot be approved from status '{application.status}'."
        )

    applicant = db.session.get(User, application.user_id)
    _require_active_user(applicant, "Applicant")
    _require_active_user(reviewer_user, "Reviewer")

    institution_id, department_id, programme_id = _validate_requested_scope(
        application
    )

    existing = _find_existing_assignment(
        application,
        institution_id,
        department_id,
        programme_id,
    )

    if existing is not None:
        raise RoleApprovalError(
            "This user already has an approved assignment for the same role and scope."
        )

    now = _utcnow()

    assignment = UserRoleAssignment(
        user_id=application.user_id,
        role_id=application.requested_role_id,
        institution_id=institution_id,
        department_id=department_id,
        programme_id=programme_id,
        status=APPROVED_ASSIGNMENT_STATUS,
        academic_session=application.academic_session,
        approved_by_user_id=reviewer_user.id,
        approved_at=now,
        expires_at=expires_at,
    )

    application.status = RoleApplication.STATUS_APPROVED
    application.reviewed_by_user_id = reviewer_user.id
    application.reviewer_notes = reviewer_notes
    application.decided_at = now

    db.session.add(assignment)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return assignment
