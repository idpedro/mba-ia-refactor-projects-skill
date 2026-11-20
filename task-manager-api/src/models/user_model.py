from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from src.constants import ROLE_ADMIN, ROLE_USER
from src.database import db
from src.models import legacy_password
from src.models.base import utcnow


class User(db.Model):
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

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if legacy_password.is_wrapped(self.password):
            return legacy_password.check_wrapped(self.password, raw_password)
        return check_password_hash(self.password, raw_password)

    def has_legacy_password(self):
        return legacy_password.is_wrapped(self.password)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    @classmethod
    def get(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def find_by_email(cls, email):
        return db.session.scalar(select(cls).where(func.lower(cls.email) == email.lower()))

    @classmethod
    def email_taken(cls, email, exclude_id=None):
        query = select(cls.id).where(func.lower(cls.email) == email.lower())
        if exclude_id is not None:
            query = query.where(cls.id != exclude_id)
        return db.session.scalar(query) is not None

    @classmethod
    def list_all(cls):
        return db.session.scalars(select(cls).order_by(cls.id)).all()

    @classmethod
    def list_with_task_counts(cls):
        from src.models.task_model import Task

        rows = db.session.execute(
            select(cls, func.count(Task.id))
            .outerjoin(Task, Task.user_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
        ).all()
        return [(user, task_count) for user, task_count in rows]

    @classmethod
    def count(cls):
        return db.session.scalar(select(func.count(cls.id)))
