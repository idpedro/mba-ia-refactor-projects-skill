"""Objeto de banco (Flask-SQLAlchemy) e inicialização do schema."""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """UTC "naive", no mesmo formato dos valores já gravados no SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db(app):
    db.init_app(app)
    with app.app_context():
        import src.models  # noqa: F401  registra os models antes do create_all
        db.create_all()
