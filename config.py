import os
from pathlib import Path


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration with safe defaults."""

    # Development may fall back to this value.
    # Production overrides this and requires SECRET_KEY explicitly.
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-only-change-me",
    )

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # SQLite Database configuration
    INSTANCE_DIR = BASE_DIR / "instance"
    INSTANCE_DIR.mkdir(exist_ok=True)

    _db_path = (INSTANCE_DIR / "database.db").as_posix()

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_db_path}",
    )

    # If DATABASE_URL was set to a relative instance path,
    # normalize it to the absolute project instance path.
    if SQLALCHEMY_DATABASE_URI.startswith(
        "sqlite:///instance/"
    ):
        SQLALCHEMY_DATABASE_URI = (
            f"sqlite:///{_db_path}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Placement Web Search API Configuration
    SEARCH_API_KEY = os.environ.get(
        "SEARCH_API_KEY",
        None,
    )

    SEARCH_PROVIDER = os.environ.get(
        "SEARCH_PROVIDER",
        "none",
    )

    # Application Metadata
    APP_NAME = "Departmental SIWES Assistant"

    APP_SUBTITLE = (
        "Your guide to SIWES information, placement opportunities "
        "and industrial training support."
    )

    SIWES_DURATION_MONTHS = 6


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing configuration with isolated in-memory database."""

    TESTING = True

    # Tests should never depend on a real/private secret.
    SECRET_KEY = "dsa-test-secret-key"

    WTF_CSRF_ENABLED = False

    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    # Production must receive its secret from the environment.
    # create_app() validates that this value exists.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}