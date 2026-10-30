from sqlalchemy.orm import joinedload

from src.database import db, utcnow

TASK_STATUSES = ("pending", "in_progress", "done", "cancelled")
STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED = TASK_STATUSES
CLOSED_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 e 2 contam como "alta prioridade"
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}
DUE_DATE_FORMAT = "%Y-%m-%d"
TAG_SEPARATOR = ","


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", backref="tasks")
    category = db.relationship("Category", backref="tasks")

    # ---- regras da entidade -------------------------------------------------
    def is_overdue(self, now=None):
        now = now or utcnow()
        return self.due_date is not None and self.due_date < now and self.status not in CLOSED_STATUSES

    def days_overdue(self, now=None):
        return ((now or utcnow()) - self.due_date).days

    @staticmethod
    def join_tags(tags):
        return TAG_SEPARATOR.join(tags) if isinstance(tags, list) else tags

    # ---- serialização --------------------------------------------------------
    def to_dict(self, include_overdue=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tags.split(TAG_SEPARATOR) if self.tags else [],
        }
        if include_overdue:
            data["overdue"] = self.is_overdue()
        return data

    def to_summary_dict(self):
        """Formato reduzido usado por GET /users/<id>/tasks."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": str(self.created_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "overdue": self.is_overdue(),
        }

    # ---- consultas -----------------------------------------------------------
    @classmethod
    def get(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def all_with_relations(cls):
        stmt = db.select(cls).options(joinedload(cls.user), joinedload(cls.category)).order_by(cls.id)
        return db.session.scalars(stmt).unique().all()

    @classmethod
    def all(cls):
        return db.session.scalars(db.select(cls).order_by(cls.id)).all()

    @classmethod
    def by_user(cls, user_id):
        return db.session.scalars(db.select(cls).where(cls.user_id == user_id).order_by(cls.id)).all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        stmt = db.select(cls)
        if text:
            pattern = f"%{text}%"
            stmt = stmt.where(db.or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            stmt = stmt.where(cls.status == status)
        if priority is not None:
            stmt = stmt.where(cls.priority == priority)
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        return db.session.scalars(stmt.order_by(cls.id)).all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(db.func.count(cls.id)))

    @classmethod
    def count_by(cls, column):
        rows = db.session.execute(db.select(column, db.func.count(cls.id)).group_by(column)).all()
        return {key: total for key, total in rows}

    @classmethod
    def count_by_status(cls):
        return cls.count_by(cls.status)

    @classmethod
    def count_by_priority(cls):
        return cls.count_by(cls.priority)

    @classmethod
    def count_by_user(cls):
        return cls.count_by(cls.user_id)

    @classmethod
    def count_by_category(cls):
        return cls.count_by(cls.category_id)

    @classmethod
    def count_created_since(cls, since):
        return db.session.scalar(db.select(db.func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_done_since(cls, since):
        return db.session.scalar(
            db.select(db.func.count(cls.id)).where(cls.status == STATUS_DONE, cls.updated_at >= since)
        )

    @classmethod
    def clear_category(cls, category_id):
        db.session.execute(db.update(cls).where(cls.category_id == category_id).values(category_id=None))

    @classmethod
    def delete_by_user(cls, user_id):
        db.session.execute(db.delete(cls).where(cls.user_id == user_id))
