"""Configuração da aplicação, lida do ambiente (ver .env.example).

Nenhum segredo tem valor literal: a chave de assinatura é gerada no boot quando
ausente, e o SMTP fica desligado enquanto as credenciais não forem informadas.
"""
import os
import secrets


def _list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "86400"))

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    # Lista explícita de origens liberadas; vazia = nenhum acesso cross-origin.
    CORS_ORIGINS = _list("CORS_ORIGINS")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_TIMEOUT = int(os.environ.get("SMTP_TIMEOUT", "10"))

    # Senhas das contas semeadas; ausentes = geradas e exibidas uma única vez.
    SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD")
    SEED_USER_PASSWORD = os.environ.get("SEED_USER_PASSWORD")
