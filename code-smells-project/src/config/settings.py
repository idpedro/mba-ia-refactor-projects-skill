import os
import secrets


class Settings:
    # Sem SECRET_KEY no ambiente, gera uma chave aleatória por boot (tokens expiram a cada reinício).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000"
    ).split(",")
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "86400"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    APP_VERSION = "1.0.0"
    AMBIENTE = os.environ.get("AMBIENTE", "producao")
