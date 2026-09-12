"""
Authorization service for DSA.

Authorization is based on:
    role + permission + approved assignment + scope + expiry

Important design rules:
- A role title alone never grants access.
- Pending, suspended, revoked, or expired assignments grant nothing.
- Scope is enforced server-side.
- A department must belong to the requested institution.
- A programme must belong to the requested department/institution.
- Global access is not implied by being a Platform Administrator.
  The role must still carry the requested permission explicitly.
"""

from datetime import datetime

from models.access import UserRoleAssignment
from models.academic import Department, Programme


APPROVED_ASSIGNMENT_STATUS = "Approved"
ACTIVE_ACCOUNT_STATUS = "Active"


def _utcnow():
    """Return a naive UTC datetime compatible with the project's current models."""
    return datetime.utcnow()


def _normalise_id(value):
    """Convert an ID-like value to int when possible; otherwise return None."""
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_target_scope(
    institution_id=None,
    department_id=None,
    programme_id=None,
):
    """
    Resolve and validate the requested hierarchy.

    Returns:
        (is_valid, resolved_institution_id, resolved_department_id, resolved_programme_id)

    Examples:
    - If only programme_id is supplied, department and institution are derived.
    - If programme_id and department_id disagree, access is denied.
    - If department_id and institution_id disagree, access is denied.
    """
    institution_id = _normalise_id(institution_id)
    department_id = _normalise_id(department_id)
    programme_id = _normalise_id(programme_id)

    resolved_institution_id = institution_id
    resolved_department_id = department_id
    resolved_programme_id = programme_id

    if programme_id is not None:
        programme = Programme.query.filter_by(id=programme_id).first()

        if programme is None or not programme.is_active:
            return False, None, None, None

        programme_department = programme.department

        if (
            programme_department is None
            or not programme_department.is_active
            or programme_department.academic_unit is None
            or not programme_department.academic_unit.is_active
            or programme_department.academic_unit.institution is None
            or not programme_department.academic_unit.institution.is_active
        ):
            return False, None, None, None

        derived_department_id = programme_department.id
        derived_institution_id = programme_department.academic_unit.institution_id

        if (
            department_id is not None
            and department_id != derived_department_id
        ):
            return False, None, None, None

        if (
            institution_id is not None
            and institution_id != derived_institution_id
        ):
            return False, None, None, None

        resolved_department_id = derived_department_id
        resolved_institution_id = derived_institution_id

    elif department_id is not None:
        department = Department.query.filter_by(id=department_id).first()

        if (
            department is None
            or not department.is_active
            or department.academic_unit is None
            or not department.academic_unit.is_active
            or department.academic_unit.institution is None
            or not department.academic_unit.institution.is_active
        ):
            return False, None, None, None

        derived_institution_id = department.academic_unit.institution_id

        if (
            institution_id is not None
            and institution_id != derived_institution_id
        ):
            return False, None, None, None

        resolved_institution_id = derived_institution_id

    return (
        True,
        resolved_institution_id,
        resolved_department_id,
        resolved_programme_id,
    )


def _assignment_is_current(assignment, now=None):
    """Return True only for a currently usable role assignment."""
    now = now or _utcnow()

    if assignment.status != APPROVED_ASSIGNMENT_STATUS:
        return False

    if assignment.role is None or not assignment.role.is_active:
        return False

    if assignment.expires_at is not None and assignment.expires_at <= now:
        return False

    return True


def _assignment_has_permission(assignment, permission_slug):
    """Return True when the assignment's active role explicitly carries permission."""
    if assignment.role is None:
        return False

    return (
        assignment.role.permissions
        .filter_by(slug=permission_slug)
        .first()
        is not None
    )


def _assignment_matches_scope(
    assignment,
    institution_id=None,
    department_id=None,
    programme_id=None,
):
    """
    Check whether an assignment contains the requested target scope.

    Scope rules:
    - Global assignment: institution/department/programme are all NULL.
      It can match any target, but only if the role explicitly has the permission.
    - Institution assignment: can match that institution and descendants.
    - Department assignment: can match only that department and its programmes.
    - Programme assignment: can match only that programme.
    - If no target scope is supplied, only a global assignment can authorize it.
    """
    assignment_institution_id = assignment.institution_id
    assignment_department_id = assignment.department_id
    assignment_programme_id = assignment.programme_id

    target_has_scope = any(
        value is not None
        for value in (institution_id, department_id, programme_id)
    )

    assignment_is_global = all(
        value is None
        for value in (
            assignment_institution_id,
            assignment_department_id,
            assignment_programme_id,
        )
    )

    if not target_has_scope:
        return assignment_is_global

    if assignment_is_global:
        return True

    if assignment_institution_id is not None:
        if institution_id != assignment_institution_id:
            return False

    if assignment_department_id is not None:
        if department_id != assignment_department_id:
            return False

    if assignment_programme_id is not None:
        if programme_id != assignment_programme_id:
            return False

    return True


def user_has_permission(
    user,
    permission_slug,
    institution_id=None,
    department_id=None,
    programme_id=None,
):
    """
    Determine whether a user has a permission for a specific scope.

    Args:
        user:
            User model instance.

        permission_slug:
            Permission slug such as "view_department_students".

        institution_id:
            Optional institution target.

        department_id:
            Optional department target.

        programme_id:
            Optional programme target.

    Returns:
        bool

    Security behavior:
    - inactive/nonexistent users are denied;
    - malformed IDs are denied;
    - invalid hierarchy combinations are denied;
    - only Approved, unexpired assignments count;
    - the role must be active;
    - the requested permission must be explicitly attached to the role;
    - assignment scope must contain the requested target.
    """
    if user is None or getattr(user, "id", None) is None:
        return False

    if getattr(user, "account_status", ACTIVE_ACCOUNT_STATUS) != ACTIVE_ACCOUNT_STATUS:
        return False

    if not isinstance(permission_slug, str) or not permission_slug.strip():
        return False

    # Detect malformed non-null IDs before normalisation silently turns them into None.
    raw_ids = (institution_id, department_id, programme_id)
    normalised_ids = tuple(_normalise_id(value) for value in raw_ids)

    for raw_value, normalised_value in zip(raw_ids, normalised_ids):
        if raw_value is not None and normalised_value is None:
            return False

    (
        institution_id,
        department_id,
        programme_id,
    ) = normalised_ids

    (
        scope_is_valid,
        institution_id,
        department_id,
        programme_id,
    ) = _resolve_target_scope(
        institution_id=institution_id,
        department_id=department_id,
        programme_id=programme_id,
    )

    if not scope_is_valid:
        return False

    assignments = (
        UserRoleAssignment.query
        .filter_by(user_id=user.id)
        .all()
    )

    now = _utcnow()

    for assignment in assignments:
        if not _assignment_is_current(assignment, now=now):
            continue

        if not _assignment_has_permission(assignment, permission_slug):
            continue

        if not _assignment_matches_scope(
            assignment,
            institution_id=institution_id,
            department_id=department_id,
            programme_id=programme_id,
        ):
            continue

        return True

    return False


def require_permission_for_scope(
    user,
    permission_slug,
    institution_id=None,
    department_id=None,
    programme_id=None,
):
    """
    Convenience wrapper.

    Returns True/False just like user_has_permission().
    It exists so route-level code can use a readable service name now,
    while a Flask decorator/403 helper can be added later without changing
    the core authorization rules.
    """
    return user_has_permission(
        user=user,
        permission_slug=permission_slug,
        institution_id=institution_id,
        department_id=department_id,
        programme_id=programme_id,
    )
