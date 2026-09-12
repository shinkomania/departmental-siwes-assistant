"""
Models Package
--------------
Exports the shared database instance and all application data models.
"""
from .db import db
from .student import StudentProfile
from .organization import Organization
from .application import SavedOrganization, PlacementApplication
from .guide import GuideTopic
from .academic import Institution, AcademicUnit, Department, Programme, SIWESConfiguration
from .user import User
from .access import Role, Permission, UserRoleAssignment, role_permissions

__all__ = [
    'User',
    'db',
    'StudentProfile',
    'Organization',
    'SavedOrganization',
    'PlacementApplication',
    'GuideTopic',
    'Institution',
    'AcademicUnit',
    'Department',
    'Programme',
    'SIWESConfiguration'
    'Role',
    'Permission',
    'UserRoleAssignment',
    'role_permissions'
]
