"""Configuração da aplicação, lida do ambiente (com defaults seguros para desenvolvimento)."""
import os
import secrets

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv é opcional em runtime
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _flag("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Quando ligado, rotas de escrita exigem `Authorization: Bearer <token>` (decisão 4).
    AUTH_REQUIRED = _flag("AUTH_REQUIRED")
    AUTH_TOKEN_MAX_AGE = int(os.environ.get("AUTH_TOKEN_MAX_AGE", str(60 * 60 * 24)))

    # Sem SMTP_HOST o NotificationService apenas registra em log (decisão 8).
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
