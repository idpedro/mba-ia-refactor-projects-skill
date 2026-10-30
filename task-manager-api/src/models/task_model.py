from sqlalchemy.orm import joinedload

from src.database import db, utcnow

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
VALID_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
CLOSED_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200


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

    def is_overdue(self, now=None):
        return (
            self.due_date is not None
            and self.due_date < (now or utcnow())
            and self.status not in CLOSED_STATUSES
        )

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
            "tags": self.tags.split(",") if self.tags else [],
        }
        if include_overdue:
            data["overdue"] = self.is_overdue()
        return data

    def to_summary_dict(self):
        """Formato reduzido usado em /users/<id>/tasks."""
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


def get_task(task_id):
    return db.session.get(Task, task_id)


def list_tasks_with_relations():
    query = db.select(Task).options(joinedload(Task.user), joinedload(Task.category)).order_by(Task.id)
    return db.session.scalars(query).unique().all()


def list_tasks_by_user(user_id):
    return db.session.scalars(db.select(Task).filter_by(user_id=user_id).order_by(Task.id)).all()


def search_tasks(text=None, status=None, priority=None, user_id=None):
    query = db.select(Task)
    if text:
        pattern = f"%{text}%"
        query = query.where(db.or_(Task.title.like(pattern), Task.description.like(pattern)))
    if status:
        query = query.where(Task.status == status)
    if priority is not None:
        query = query.where(Task.priority == priority)
    if user_id is not None:
        query = query.where(Task.user_id == user_id)
    return db.session.scalars(query.order_by(Task.id)).all()


def list_overdue_tasks(now):
    query = db.select(Task).where(
        Task.due_date.is_not(None), Task.due_date < now, Task.status.not_in(CLOSED_STATUSES)
    ).order_by(Task.id)
    return db.session.scalars(query).all()


def count_tasks(*conditions):
    return db.session.scalar(db.select(db.func.count(Task.id)).where(*conditions))


def count_tasks_by(column):
    return dict(db.session.execute(db.select(column, db.func.count(Task.id)).group_by(column)).all())


def count_overdue_tasks(now):
    return count_tasks(Task.due_date.is_not(None), Task.due_date < now, Task.status.not_in(CLOSED_STATUSES))


def completion_by_user():
    """{user_id: (total, done)} numa única query."""
    done = db.func.sum(db.case((Task.status == STATUS_DONE, 1), else_=0))
    rows = db.session.execute(
        db.select(Task.user_id, db.func.count(Task.id), done).where(Task.user_id.is_not(None)).group_by(Task.user_id)
    ).all()
    return {user_id: (total, int(done_count or 0)) for user_id, total, done_count in rows}


def save(task):
    db.session.add(task)
    db.session.commit()
    return task


def delete(task):
    db.session.delete(task)
    db.session.commit()
