from sqlalchemy import func, select, update

from src.config.settings import DEFAULT_CATEGORY_COLOR
from src.database import db, utcnow
from src.models.base import PersistentMixin
from src.models.task_model import Task


class Category(PersistentMixin, db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_CATEGORY_COLOR)
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
        statement = (
            select(cls, func.count(Task.id))
            .outerjoin(Task, Task.category_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
        )
        return db.session.execute(statement).all()

    def delete_detaching_tasks(self):
        """Delete the category and clear it from its tasks in one transaction."""
        try:
            db.session.execute(update(Task).where(Task.category_id == self.id).values(category_id=None))
            db.session.delete(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
