"""Agregações de relatórios (regras que cruzam tasks, usuários e categorias)."""
from datetime import timedelta

from src.database import utcnow
from src.models.task_model import (
    HIGH_PRIORITY_MAX,
    PRIORITY_LABELS,
    STATUS_DONE,
    TASK_STATUSES,
)

RECENT_ACTIVITY_DAYS = 7


def completion_rate(done, total):
    return round((done / total) * 100, 2) if total > 0 else 0


class ReportService:
    def __init__(self, task_model, user_model, category_model):
        self.tasks = task_model
        self.users = user_model
        self.categories = category_model

    def status_counts(self):
        counts = self.tasks.count_by_status()
        return {status: counts.get(status, 0) for status in TASK_STATUSES}

    def task_stats(self):
        total = self.tasks.count()
        by_status = self.status_counts()
        now = utcnow()
        overdue = sum(1 for task in self.tasks.all() if task.is_overdue(now))
        return {
            "total": total,
            **by_status,
            "overdue": overdue,
            "completion_rate": completion_rate(by_status[STATUS_DONE], total),
        }

    def summary(self):
        now = utcnow()
        all_tasks = self.tasks.all()
        overdue_tasks = [task for task in all_tasks if task.is_overdue(now)]
        by_priority = self.tasks.count_by_priority()
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

        done_by_user = {}
        for task in all_tasks:
            if task.status == STATUS_DONE:
                done_by_user[task.user_id] = done_by_user.get(task.user_id, 0) + 1
        total_by_user = self.tasks.count_by_user()

        user_productivity = []
        for user in self.users.all():
            total = total_by_user.get(user.id, 0)
            completed = done_by_user.get(user.id, 0)
            user_productivity.append({
                "user_id": user.id,
                "user_name": user.name,
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_rate": completion_rate(completed, total),
            })

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": len(all_tasks),
                "total_users": self.users.count(),
                "total_categories": self.categories.count(),
            },
            "tasks_by_status": self.status_counts(),
            "tasks_by_priority": {label: by_priority.get(level, 0) for level, label in PRIORITY_LABELS.items()},
            "overdue": {
                "count": len(overdue_tasks),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "due_date": str(task.due_date),
                        "days_overdue": task.days_overdue(now),
                    }
                    for task in overdue_tasks
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": self.tasks.count_created_since(since),
                "tasks_completed_last_7_days": self.tasks.count_done_since(since),
            },
            "user_productivity": user_productivity,
        }

    def user_report(self, user):
        tasks = self.tasks.by_user(user.id)
        now = utcnow()
        by_status = {status: 0 for status in TASK_STATUSES}
        for task in tasks:
            if task.status in by_status:
                by_status[task.status] += 1
        total = len(tasks)
        return {
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "statistics": {
                "total_tasks": total,
                **by_status,
                "overdue": sum(1 for task in tasks if task.is_overdue(now)),
                "high_priority": sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
                "completion_rate": completion_rate(by_status[STATUS_DONE], total),
            },
        }
