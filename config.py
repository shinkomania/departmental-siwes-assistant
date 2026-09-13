import os
from pathlib import Path


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration with safe defaults."""

    SECRET_KEY = os.environ.get(
        'SECRET_KEY',
        'dev-only-change-me',
    )

    # SQLite Database configuration
    INSTANCE_DIR = BASE_DIR / 'instance'
    INSTANCE_DIR.mkdir(exist_ok=True)

    _db_path = (INSTANCE_DIR / 'database.db').as_posix()

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{_db_path}",
    )

    # If DATABASE_URL was set to a relative instance path,
    # normalize it to the absolute project instance path.
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite:///instance/'):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_db_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Placement Web Search API Configuration
    # Supports extensible providers such as:
    # SerpAPI, Tavily, Google Custom Search, etc.
    SEARCH_API_KEY = os.environ.get(
        'SEARCH_API_KEY',
        None,
    )
    SEARCH_PROVIDER = os.environ.get(
        'SEARCH_PROVIDER',
        'none',
    )

    # Application Metadata
    APP_NAME = "Departmental SIWES Assistant"
    APP_SUBTITLE = (
        "Your guide to SIWES information, placement opportunities "
        "and industrial training support."
    )

    SIWES_DURATION_MONTHS = 6


class DevelopmentConfig(Config):
    """Development configuration with debug enabled."""

    DEBUG = True


class TestingConfig(Config):
    """Testing configuration with in-memory database."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}