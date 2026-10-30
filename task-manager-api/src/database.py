from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """UTC sem tzinfo, no mesmo formato das datas já gravadas no SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db(app):
    db.init_app(app)
    with app.app_context():
        from src import models  # noqa: F401 — registra as tabelas antes do create_all
        db.create_all()
