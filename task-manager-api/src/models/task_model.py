from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import joinedload

from src.constants import DEFAULT_PRIORITY, FINAL_STATUSES, STATUS_PENDING
from src.database import db
from src.models.base import utcnow


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def is_overdue(self):
        return (
            self.due_date is not None
            and self.due_date < utcnow()
            and self.status not in FINAL_STATUSES
        )

    def to_dict(self, include_overdue=False, include_names=False, fields=None):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }
        if fields is not None:
            data = {key: data[key] for key in fields}
        if include_overdue:
            data['overdue'] = self.is_overdue()
        if include_names:
            data['user_name'] = self.user.name if self.user else None
            data['category_name'] = self.category.name if self.category else None
        return data

    @classmethod
    def get(cls, task_id):
        return db.session.get(cls, task_id)

    @staticmethod
    def _owned_by(query, owner_id):
        return query if owner_id is None else query.where(Task.user_id == owner_id)

    @classmethod
    def list_all(cls, owner_id=None, with_relations=False):
        query = cls._owned_by(select(cls), owner_id).order_by(cls.id)
        if with_relations:
            query = query.options(joinedload(cls.user), joinedload(cls.category))
        return db.session.scalars(query).unique().all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, owner_id=None):
        query = cls._owned_by(select(cls), owner_id)
        if text:
            # O termo vai como parâmetro vinculado; não há SQL montado com strings.
            pattern = f'%{text}%'
            query = query.where(or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        return db.session.scalars(query.order_by(cls.id)).all()

    @classmethod
    def count_by(cls, column, owner_id=None):
        rows = db.session.execute(
            cls._owned_by(select(column, func.count(cls.id)), owner_id).group_by(column)
        ).all()
        return dict(rows)

    @classmethod
    def count_by_user_and_status(cls):
        rows = db.session.execute(
            select(cls.user_id, cls.status, func.count(cls.id)).group_by(cls.user_id, cls.status)
        ).all()
        return {(user_id, status): total for user_id, status, total in rows}

    @classmethod
    def count_since(cls, column, since, status=None):
        query = select(func.count(cls.id)).where(column >= since)
        if status is not None:
            query = query.where(cls.status == status)
        return db.session.scalar(query)

    @classmethod
    def count(cls):
        return db.session.scalar(select(func.count(cls.id)))

    @classmethod
    def delete_for_user(cls, user_id):
        for task in db.session.scalars(select(cls).where(cls.user_id == user_id)):
            db.session.delete(task)

    @classmethod
    def clear_category(cls, category_id):
        db.session.execute(
            update(cls).where(cls.category_id == category_id).values(category_id=None)
        )
