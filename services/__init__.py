"""
Services Package
----------------
Contains business logic, external search adapters, authorization,
and administrative workflow services.
"""

from .placement_search import PlacementSearchService
from .authorization import user_has_permission, require_permission_for_scope
from .role_application import (
    RoleApplicationSubmissionError,
    submit_role_application,
)
from .role_approval import (
    RoleApprovalError,
    approve_role_application,
)
from .role_review import (
    RoleReviewError,
    mark_role_application_under_review,
    request_role_application_more_information,
    reject_role_application,
    withdraw_role_application,
)

__all__ = [
    "PlacementSearchService",
    "user_has_permission",
    "require_permission_for_scope",
    "RoleApplicationSubmissionError",
    "submit_role_application",
    "RoleApprovalError",
    "approve_role_application",
    "RoleReviewError",
    "mark_role_application_under_review",
    "request_role_application_more_information",
    "reject_role_application",
    "withdraw_role_application",
]
