"""
Departmental SIWES Assistant (DSA)
==================================
Main Application Entry Point and Flask App Factory.

Author: Departmental SIWES Project Team
License: MIT
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, session
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config import config_by_name
from models.db import db
from models import (
    User,
    StudentProfile,
    Institution,
    AcademicUnit,
    Department,
    Programme,
    SIWESConfiguration,
)
from routes import (
    main_bp,
    student_bp,
    placement_bp,
    admin_bp,
    auth_bp,
)

from services.authorization import user_has_permission

migrate = Migrate()
csrf = CSRFProtect()

# Load environment variables from .env file
load_dotenv()


def create_app(config_name=None):
    """
    Application Factory Function.
    Creates and configures the Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)

    # Load configuration class
    app_config = config_by_name.get(
        config_name,
        config_by_name["default"],
    )
    app.config.from_object(app_config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(placement_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

        # Context processor
    @app.context_processor
    def inject_global_context():
        """
        Provide common application metadata and authenticated
        user/student information to templates.

        Student identity is resolved only through:

            authenticated User -> StudentProfile

        Platform administration visibility is derived from the
        explicit access_platform_admin_panel permission.

        Legacy session flags such as session['student_id'] and
        session['is_admin'] are not trusted.
        """
        user_id = session.get("user_id")

        current_user = None
        current_student = None
        can_access_platform_admin = False

        if user_id:
            current_user = db.session.get(User, user_id)

            if (
                current_user is not None
                and current_user.account_status != "Active"
            ):
                current_user = None

        if current_user:
            current_student = StudentProfile.query.filter_by(
                user_id=current_user.id
            ).first()

            can_access_platform_admin = user_has_permission(
                current_user,
                "access_platform_admin_panel",
            )

        return {
            "app_name": app.config.get(
                "APP_NAME",
                "Departmental SIWES Assistant",
            ),
            "app_subtitle": app.config.get(
                "APP_SUBTITLE",
                "",
            ),
            "current_year": datetime.utcnow().year,
            "current_user": current_user,
            "current_student": current_student,
            "can_access_platform_admin": can_access_platform_admin,
        }

    # Markdown rendering
    import markdown as md_parser

    @app.template_filter("markdown")
    def render_markdown(text):
        if not text:
            return ""

        return md_parser.markdown(
            text,
            extensions=["extra", "nl2br"],
        )

    # Status badge helper
    @app.template_filter("badge_class")
    def badge_class_filter(status):
        """
        Converts application/review/status values to CSS badge classes.

        Legacy organization verification values remain temporarily
        supported while organization templates are migrated.
        """
        mapping = {
            # Legacy organization statuses
            "Verified": "badge-verified",
            "Online Source": "badge-online",
            "Student Submitted": "badge-student",

            # Placement statuses
            "Interested": "badge-interested",
            "Contacted": "badge-contacted",
            "Application Submitted": "badge-applied",
            "Interview": "badge-interview",
            "Accepted": "badge-accepted",
            "Rejected": "badge-rejected",

            # Administrative application statuses
            "Submitted": "badge-default",
            "Pending Verification": "badge-default",
            "Under Review": "badge-default",
            "More Info Required": "badge-default",
            "Approved": "badge-accepted",
            "Withdrawn": "badge-default",
        }

        return mapping.get(status, "badge-default")

    @app.cli.command("init-db")
    def init_db_command():
        """
        Database schema is managed through Flask-Migrate/Alembic.
        """
        print(
            "DSA database schema is managed with migrations. "
            "Use: flask db upgrade"
        )

    @app.cli.command("seed-db")
    def seed_db_command():
        """
        Populate existing database tables with DSA seed data.

        Schema creation is handled exclusively by migrations.
        """
        from seed import seed_database

        seed_database(app)

    return app


if __name__ == "__main__":
    application = create_app("development")

    port = int(os.environ.get("PORT", 5000))

    print(
        "\n"
        "=======================================================\n"
        " Starting Departmental SIWES Assistant (DSA)...\n"
        f" Access URL: http://127.0.0.1:{port}\n"
        "=======================================================\n"
    )

    application.run(
        host="127.0.0.1",
        port=port,
        debug=True,
    )