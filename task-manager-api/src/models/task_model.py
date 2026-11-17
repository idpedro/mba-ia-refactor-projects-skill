from sqlalchemy import case, func, select
from sqlalchemy.orm import joinedload

from src.config.settings import CLOSED_TASK_STATUSES, DEFAULT_PRIORITY, TASK_STATUS_DONE, TASK_STATUS_PENDING
from src.database import db, utcnow
from src.models.base import PersistentMixin


class Task(PersistentMixin, db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=TASK_STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    # ---- entity rules and serialization -------------------------------

    def is_overdue(self, now=None):
        now = now or utcnow()
        return bool(self.due_date and self.due_date < now and self.status not in CLOSED_TASK_STATUSES)

    def to_dict(self, include_overdue=False):
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
        if include_overdue:
            data['overdue'] = self.is_overdue()
        return data

    def to_listing_dict(self):
        data = self.to_dict(include_overdue=True)
        data['user_name'] = self.user.name if self.user else None
        data['category_name'] = self.category.name if self.category else None
        return data

    def to_summary_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'overdue': self.is_overdue(),
        }

    # ---- queries -------------------------------------------------------

    @classmethod
    def get(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def list_with_relations(cls):
        statement = select(cls).options(joinedload(cls.user), joinedload(cls.category)).order_by(cls.id)
        return db.session.scalars(statement).unique().all()

    @classmethod
    def for_user(cls, user_id):
        return db.session.scalars(select(cls).where(cls.user_id == user_id).order_by(cls.id)).all()

    @classmethod
    def search(cls, text='', status='', priority=None, user_id=None):
        statement = select(cls)
        if text:
            statement = statement.where(db.or_(cls.title.like(f'%{text}%'), cls.description.like(f'%{text}%')))
        if status:
            statement = statement.where(cls.status == status)
        if priority is not None:
            statement = statement.where(cls.priority == priority)
        if user_id is not None:
            statement = statement.where(cls.user_id == user_id)
        return db.session.scalars(statement.order_by(cls.id)).all()

    @classmethod
    def counts_by_status(cls):
        rows = db.session.execute(select(cls.status, func.count(cls.id)).group_by(cls.status)).all()
        return {status: count for status, count in rows}

    @classmethod
    def counts_by_priority(cls):
        rows = db.session.execute(select(cls.priority, func.count(cls.id)).group_by(cls.priority)).all()
        return {priority: count for priority, count in rows}

    @classmethod
    def _overdue_clause(cls, now):
        return db.and_(cls.due_date.isnot(None), cls.due_date < now, cls.status.notin_(CLOSED_TASK_STATUSES))

    @classmethod
    def count_overdue(cls, now):
        return db.session.scalar(select(func.count(cls.id)).where(cls._overdue_clause(now)))

    @classmethod
    def overdue_tasks(cls, now):
        return db.session.scalars(select(cls).where(cls._overdue_clause(now)).order_by(cls.id)).all()

    @classmethod
    def count_created_since(cls, since):
        return db.session.scalar(select(func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_done_updated_since(cls, since):
        return db.session.scalar(
            select(func.count(cls.id)).where(cls.status == TASK_STATUS_DONE, cls.updated_at >= since)
        )

    @classmethod
    def per_user_counts(cls):
        """{user_id: (total, done)} in one grouped query."""
        done_sum = func.sum(case((cls.status == TASK_STATUS_DONE, 1), else_=0))
        rows = db.session.execute(
            select(cls.user_id, func.count(cls.id), done_sum).where(cls.user_id.isnot(None)).group_by(cls.user_id)
        ).all()
        return {user_id: (total, int(done or 0)) for user_id, total, done in rows}
