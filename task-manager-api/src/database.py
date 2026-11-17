from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """Naive UTC now, same format as the values already stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
