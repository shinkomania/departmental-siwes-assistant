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

__all__ = [
    'db',
    'StudentProfile',
    'Organization',
    'SavedOrganization',
    'PlacementApplication',
    'GuideTopic'
]
