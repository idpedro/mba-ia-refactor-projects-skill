from sqlalchemy import func, select

from src.constants import DEFAULT_COLOR
from src.database import db
from src.models.base import utcnow


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': str(self.created_at),
        }

    @classmethod
    def get(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def list_with_task_counts(cls):
        from src.models.task_model import Task

        return db.session.execute(
            select(cls, func.count(Task.id))
            .outerjoin(Task, Task.category_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
        ).all()

    @classmethod
    def count(cls):
        return db.session.scalar(select(func.count(cls.id)))
