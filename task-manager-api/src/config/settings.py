"""Configuração lida do ambiente (e de um .env opcional), com defaults seguros para desenvolvimento."""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _list(value):
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    # Sem SECRET_KEY no ambiente, uma chave aleatória por boot: tokens emitidos expiram no restart.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "86400"))

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = _list(os.environ.get("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
