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
from config import config_by_name
from models.db import db
from models import (
    User,
    StudentProfile,
    Institution,
    AcademicUnit,
    Department,
    Programme,
    SIWESConfiguration
)
from routes import main_bp, student_bp, placement_bp, admin_bp
migrate = Migrate()

# Load environment variables from .env file
load_dotenv()

def create_app(config_name=None):
    """
    Application Factory Function.
    Creates and configures the Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    
    # Load configuration class
    app_config = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(app_config)

    # Initialize SQLAlchemy database extension
    db.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints for modular routes
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(placement_bp)
    app.register_blueprint(admin_bp)

    # Context Processors to inject variables globally into templates
    @app.context_processor
    def inject_global_context():
        """Provides current year, application metadata, and active student profile to all templates."""
        student_id = session.get('student_id')
        current_student = None
        if student_id:
            current_student = db.session.get(StudentProfile, student_id)

        return {
            'app_name': app.config.get('APP_NAME', 'Departmental SIWES Assistant'),
            'app_subtitle': app.config.get('APP_SUBTITLE', ''),
            'current_year': datetime.utcnow().year,
            'current_student': current_student,
            'is_admin': session.get('is_admin', False)
        }

    # Custom Jinja filter for Markdown rendering
    import markdown as md_parser
    @app.template_filter('markdown')
    def render_markdown(text):
        if not text:
            return ""
        return md_parser.markdown(text, extensions=['extra', 'nl2br'])

    # Custom Jinja filters
    @app.template_filter('badge_class')
    def badge_class_filter(status):
        """Converts verification status to CSS badge classes."""
        mapping = {
            'Verified': 'badge-verified',
            'Online Source': 'badge-online',
            'Student Submitted': 'badge-student',
            'Interested': 'badge-interested',
            'Contacted': 'badge-contacted',
            'Application Submitted': 'badge-applied',
            'Interview': 'badge-interview',
            'Accepted': 'badge-accepted',
            'Rejected': 'badge-rejected'
        }
        return mapping.get(status, 'badge-default')

    # CLI Command to create database tables
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize and create all database tables."""
        with app.app_context():
            db.create_all()
            print("Database initialized successfully!")

    # CLI Command to seed database
    @app.cli.command('seed-db')
    def seed_db_command():
        """Populate database with SIWES guides and verified organizations."""
        from seed import seed_database
        with app.app_context():
            db.create_all()
            seed_database(app)

    # Auto-create tables on startup in development mode
    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    # When executed directly, run the development server
    application = create_app('development')
    port = int(os.environ.get('PORT', 5000))
    print(f"\n=======================================================")
    print(f" Starting Departmental SIWES Assistant (DSA)...")
    print(f" Access URL: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    application.run(host='127.0.0.1', port=port, debug=True)
