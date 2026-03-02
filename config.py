import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration class"""

    # Flask Secret Key (change this in production!)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Check if we should use SQLite (for local development)
    USE_SQLITE = os.environ.get('USE_SQLITE', 'false').lower() == 'true'

    # Database Configuration
    if USE_SQLITE:
        # SQLite for local development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///rcdevdash.db'
        # SQLite-specific engine options
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
        }
    else:
        # MySQL for PythonAnywhere production
        DB_USERNAME = os.environ.get('DB_USERNAME', 'your_username')
        DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_password')
        DB_HOST = os.environ.get('DB_HOST', 'your_username.mysql.pythonanywhere-services.com')
        DB_NAME = os.environ.get('DB_NAME', 'your_username$rcdevdash')
        SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
        # MySQL-specific engine options for connection pool management
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,  # Enable connection health checks before checkout
            'pool_recycle': 3600,   # Recycle connections after 1 hour (prevents stale connections)
            'pool_size': 10,        # Maximum number of permanent connections
            'max_overflow': 20,     # Maximum overflow connections
            'connect_args': {
                'connect_timeout': 10  # Connection timeout in seconds
            }
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query debugging

    # Session Configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour in seconds

    # Application Settings
    ITEMS_PER_PAGE = 50
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
