import os
import secrets


def _flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


def _lista(name, default):
    bruto = os.environ.get(name, default)
    return [item.strip() for item in bruto.split(",") if item.strip()]


class Settings:
    # Sem SECRET_KEY no ambiente, cada boot gera uma chave aleatória: tokens antigos deixam de valer.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _flag("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = _lista("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "86400"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    APP_VERSION = "1.0.0"
    ENVIRONMENT = os.environ.get("APP_ENV", "development")
