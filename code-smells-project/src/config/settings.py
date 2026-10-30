import os
import secrets


def _flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Every environment-dependent value. Secrets come only from the environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _flag("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]
    ADMIN_ENABLED = _flag("ADMIN_ENABLED")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
    APP_ENV = os.environ.get("APP_ENV", "producao")
