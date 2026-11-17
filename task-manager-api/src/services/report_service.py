from datetime import timedelta

from src.config.settings import (
    HIGH_PRIORITY_MAX,
    RECENT_ACTIVITY_DAYS,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_PENDING,
)
from src.database import utcnow


def completion_rate(done, total):
    return round((done / total) * 100, 2) if total > 0 else 0


class ReportService:
    """Aggregations over tasks, users and categories."""

    def __init__(self, tasks, users, categories):
        self.tasks = tasks
        self.users = users
        self.categories = categories

    def task_stats(self):
        by_status = self.tasks.counts_by_status()
        total = sum(by_status.values())
        done = by_status.get(TASK_STATUS_DONE, 0)
        return {
            'total': total,
            'pending': by_status.get(TASK_STATUS_PENDING, 0),
            'in_progress': by_status.get(TASK_STATUS_IN_PROGRESS, 0),
            'done': done,
            'cancelled': by_status.get(TASK_STATUS_CANCELLED, 0),
            'overdue': self.tasks.count_overdue(utcnow()),
            'completion_rate': completion_rate(done, total),
        }

    def summary(self):
        now = utcnow()
        by_status = self.tasks.counts_by_status()
        by_priority = self.tasks.counts_by_priority()
        users = self.users.list_all()
        per_user = self.tasks.per_user_counts()
        overdue = self.tasks.overdue_tasks(now)
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

        user_stats = []
        for user in users:
            total, done = per_user.get(user.id, (0, 0))
            user_stats.append({
                'user_id': user.id,
                'user_name': user.name,
                'total_tasks': total,
                'completed_tasks': done,
                'completion_rate': completion_rate(done, total),
            })

        return {
            'generated_at': str(now),
            'overview': {
                'total_tasks': sum(by_status.values()),
                'total_users': len(users),
                'total_categories': len(self.categories.list_with_task_counts()),
            },
            'tasks_by_status': {
                'pending': by_status.get(TASK_STATUS_PENDING, 0),
                'in_progress': by_status.get(TASK_STATUS_IN_PROGRESS, 0),
                'done': by_status.get(TASK_STATUS_DONE, 0),
                'cancelled': by_status.get(TASK_STATUS_CANCELLED, 0),
            },
            'tasks_by_priority': {
                'critical': by_priority.get(1, 0),
                'high': by_priority.get(2, 0),
                'medium': by_priority.get(3, 0),
                'low': by_priority.get(4, 0),
                'minimal': by_priority.get(5, 0),
            },
            'overdue': {
                'count': len(overdue),
                'tasks': [
                    {
                        'id': task.id,
                        'title': task.title,
                        'due_date': str(task.due_date),
                        'days_overdue': (now - task.due_date).days,
                    }
                    for task in overdue
                ],
            },
            'recent_activity': {
                'tasks_created_last_7_days': self.tasks.count_created_since(since),
                'tasks_completed_last_7_days': self.tasks.count_done_updated_since(since),
            },
            'user_productivity': user_stats,
        }

    def user_report(self, user):
        tasks = self.tasks.for_user(user.id)
        now = utcnow()
        total = len(tasks)
        done = sum(1 for task in tasks if task.status == TASK_STATUS_DONE)
        return {
            'user': {'id': user.id, 'name': user.name, 'email': user.email},
            'statistics': {
                'total_tasks': total,
                'done': done,
                'pending': sum(1 for task in tasks if task.status == TASK_STATUS_PENDING),
                'in_progress': sum(1 for task in tasks if task.status == TASK_STATUS_IN_PROGRESS),
                'cancelled': sum(1 for task in tasks if task.status == TASK_STATUS_CANCELLED),
                'overdue': sum(1 for task in tasks if task.is_overdue(now)),
                'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
                'completion_rate': completion_rate(done, total),
            },
        }
