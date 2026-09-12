"""
Services Package
----------------
Contains business logic, external search adapters, authorization,
and administrative workflow services.
"""
from .placement_search import PlacementSearchService
from .authorization import user_has_permission, require_permission_for_scope
from .role_approval import (
    RoleApprovalError,
    approve_role_application,
)

__all__ = [
    'PlacementSearchService',
    'user_has_permission',
    'require_permission_for_scope',
    'RoleApprovalError',
    'approve_role_application',
]
