"""Toda configuração dependente de ambiente. Nenhum segredo tem valor literal."""
import os
import secrets


def _lista(valor):
    return [item.strip() for item in valor.split(",") if item.strip()]


class Settings:
    # Chave de assinatura dos tokens: gerada no boot quando ausente (tokens caem ao reiniciar).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    # Escutar em todas as interfaces é opt-in explícito (HOST=0.0.0.0).
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    # Lista explícita de origens; vazia = nenhum acesso cross-origin. Nunca "*".
    CORS_ORIGINS = _lista(os.environ.get("CORS_ORIGINS", ""))
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "86400"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    APP_VERSION = "1.0.0"
