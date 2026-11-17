import hashlib
import hmac

from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from src.config.settings import ROLE_ADMIN, ROLE_USER
from src.database import db, utcnow
from src.models.base import PersistentMixin
from src.models.task_model import Task

LEGACY_HASH_LENGTH = 32


def _is_legacy_hash(stored):
    return len(stored) == LEGACY_HASH_LENGTH and '$' not in stored


def _legacy_digest(raw):
    # Verify-only: accepts hashes written before the KDF migration (never used to store).
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()


class User(PersistentMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=ROLE_USER)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, raw):
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        if _is_legacy_hash(self.password):
            return hmac.compare_digest(self.password, _legacy_digest(raw))
        return check_password_hash(self.password, raw)

    def needs_rehash(self):
        return _is_legacy_hash(self.password)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    @classmethod
    def get(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def get_by_email(cls, email):
        return db.session.scalars(select(cls).where(cls.email == email)).first()

    @classmethod
    def list_all(cls):
        return db.session.scalars(select(cls).order_by(cls.id)).all()

    @classmethod
    def task_counts(cls):
        rows = db.session.execute(
            select(Task.user_id, func.count(Task.id)).where(Task.user_id.isnot(None)).group_by(Task.user_id)
        ).all()
        return {user_id: count for user_id, count in rows}

    def delete_with_tasks(self):
        """Delete the user and their tasks in one transaction."""
        try:
            for task in Task.for_user(self.id):
                db.session.delete(task)
            db.session.delete(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
