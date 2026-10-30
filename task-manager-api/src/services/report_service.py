"""Agregações de relatório e estatísticas, com GROUP BY em vez de uma query por item."""
from collections import Counter
from datetime import timedelta

from src.database import utcnow
from src.models import category_model, task_model, user_model
from src.models.task_model import (
    STATUS_CANCELLED, STATUS_DONE, STATUS_IN_PROGRESS, STATUS_PENDING, VALID_STATUSES, Task,
)

PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}
HIGH_PRIORITY_MAX = 2
RECENT_ACTIVITY_DAYS = 7


def percentage(part, total):
    return round((part / total) * 100, 2) if total > 0 else 0


class ReportService:
    def task_stats(self):
        by_status = task_model.count_tasks_by(Task.status)
        total = sum(by_status.values())
        stats = {"total": total}
        stats.update({status: by_status.get(status, 0) for status in VALID_STATUSES})
        stats["overdue"] = task_model.count_overdue_tasks(utcnow())
        stats["completion_rate"] = percentage(stats[STATUS_DONE], total)
        return stats

    def summary(self):
        now = utcnow()
        by_status = task_model.count_tasks_by(Task.status)
        by_priority = task_model.count_tasks_by(Task.priority)
        overdue = task_model.list_overdue_tasks(now)
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
        completion = task_model.completion_by_user()

        user_productivity = []
        for user in user_model.list_users():
            total, completed = completion.get(user.id, (0, 0))
            user_productivity.append({
                "user_id": user.id,
                "user_name": user.name,
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_rate": percentage(completed, total),
            })

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": sum(by_status.values()),
                "total_users": user_model.count_users(),
                "total_categories": category_model.count_categories(),
            },
            "tasks_by_status": {status: by_status.get(status, 0) for status in VALID_STATUSES},
            "tasks_by_priority": {label: by_priority.get(level, 0) for level, label in PRIORITY_LABELS.items()},
            "overdue": {
                "count": len(overdue),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "due_date": str(task.due_date),
                        "days_overdue": (now - task.due_date).days,
                    }
                    for task in overdue
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": task_model.count_tasks(Task.created_at >= since),
                "tasks_completed_last_7_days": task_model.count_tasks(
                    Task.status == STATUS_DONE, Task.updated_at >= since
                ),
            },
            "user_productivity": user_productivity,
        }

    def user_report(self, user):
        tasks = task_model.list_tasks_by_user(user.id)
        now = utcnow()
        by_status = Counter(task.status for task in tasks)
        total = len(tasks)
        return {
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "statistics": {
                "total_tasks": total,
                "done": by_status[STATUS_DONE],
                "pending": by_status[STATUS_PENDING],
                "in_progress": by_status[STATUS_IN_PROGRESS],
                "cancelled": by_status[STATUS_CANCELLED],
                "overdue": sum(1 for task in tasks if task.is_overdue(now)),
                "high_priority": sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
                "completion_rate": percentage(by_status[STATUS_DONE], total),
            },
        }
