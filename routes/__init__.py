"""
Routes Package
--------------
Exports Flask blueprints for modular URL routing.
"""

from .main import main_bp
from .student import student_bp
from .placement import placement_bp
from .admin import admin_bp
from .auth import auth_bp
from .notifications import notifications_bp

__all__ = [
    "main_bp",
    "student_bp",
    "placement_bp",
    "admin_bp",
    "auth_bp",
    "notifications_bp",
]
