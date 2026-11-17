import logging
import os
import secrets

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Domain constants
TASK_STATUS_PENDING = 'pending'
TASK_STATUS_IN_PROGRESS = 'in_progress'
TASK_STATUS_DONE = 'done'
TASK_STATUS_CANCELLED = 'cancelled'
TASK_STATUSES = (TASK_STATUS_PENDING, TASK_STATUS_IN_PROGRESS, TASK_STATUS_DONE, TASK_STATUS_CANCELLED)
CLOSED_TASK_STATUSES = (TASK_STATUS_DONE, TASK_STATUS_CANCELLED)

ROLE_USER = 'user'
ROLE_ADMIN = 'admin'
ROLE_MANAGER = 'manager'
ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2
MIN_PASSWORD_LENGTH = 4
MAX_CATEGORY_NAME_LENGTH = 100
MAX_CATEGORY_DESCRIPTION_LENGTH = 300
DEFAULT_CATEGORY_COLOR = '#000000'
RECENT_ACTIVITY_DAYS = 7
DATE_FORMAT = '%Y-%m-%d'


def _env_flag(name, default='0'):
    return os.environ.get(name, default) == '1'


class Settings:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SECRET_KEY_FROM_ENV = bool(os.environ.get('SECRET_KEY'))
    TOKEN_MAX_AGE = int(os.environ.get('TOKEN_MAX_AGE', '86400'))

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _env_flag('FLASK_DEBUG')
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', '5000'))
    CORS_ORIGINS = [origin.strip() for origin in os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',') if origin.strip()]
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    INSTANCE_PATH = os.path.join(PROJECT_ROOT, 'instance')


def configure_logging(level):
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
