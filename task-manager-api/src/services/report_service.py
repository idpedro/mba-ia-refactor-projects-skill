"""Agregações de tasks: estatísticas, relatório geral e relatório por usuário."""
from collections import Counter
from datetime import timedelta

from src.constants import (
    HIGH_PRIORITY_MAX,
    PERCENT_DECIMALS,
    PRIORITY_LABELS,
    RECENT_ACTIVITY_DAYS,
    STATUS_DONE,
    TASK_STATUSES,
)
from src.errors import NotFoundError
from src.models import Category, Task, User
from src.models.base import utcnow


def completion_rate(completed, total):
    return round((completed / total) * 100, PERCENT_DECIMALS) if total > 0 else 0


def _by_status(counts):
    return {status: counts.get(status, 0) for status in TASK_STATUSES}


class ReportService:
    def task_stats(self, owner_id=None):
        tasks = Task.list_all(owner_id=owner_id)
        by_status = _by_status(Counter(task.status for task in tasks))
        return {
            'total': len(tasks),
            **by_status,
            'overdue': sum(task.is_overdue() for task in tasks),
            'completion_rate': completion_rate(by_status[STATUS_DONE], len(tasks)),
        }

    def summary(self):
        now = utcnow()
        overdue_tasks = [task for task in Task.list_all() if task.is_overdue()]
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
        by_priority = Task.count_by(Task.priority)
        by_user_status = Task.count_by_user_and_status()

        productivity = []
        for user in User.list_all():
            total = sum(by_user_status.get((user.id, status), 0) for status in TASK_STATUSES)
            completed = by_user_status.get((user.id, STATUS_DONE), 0)
            productivity.append({
                'user_id': user.id,
                'user_name': user.name,
                'total_tasks': total,
                'completed_tasks': completed,
                'completion_rate': completion_rate(completed, total),
            })

        return {
            'generated_at': str(now),
            'overview': {
                'total_tasks': Task.count(),
                'total_users': User.count(),
                'total_categories': Category.count(),
            },
            'tasks_by_status': _by_status(Task.count_by(Task.status)),
            'tasks_by_priority': {
                label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()
            },
            'overdue': {
                'count': len(overdue_tasks),
                'tasks': [
                    {
                        'id': task.id,
                        'title': task.title,
                        'due_date': str(task.due_date),
                        'days_overdue': (now - task.due_date).days,
                    }
                    for task in overdue_tasks
                ],
            },
            'recent_activity': {
                'tasks_created_last_7_days': Task.count_since(Task.created_at, since),
                'tasks_completed_last_7_days': Task.count_since(Task.updated_at, since, STATUS_DONE),
            },
            'user_productivity': productivity,
        }

    def user_report(self, user_id):
        user = User.get(user_id)
        if user is None:
            raise NotFoundError('Usuário não encontrado')
        tasks = Task.list_all(owner_id=user_id)
        by_status = _by_status(Counter(task.status for task in tasks))
        return {
            'user': {'id': user.id, 'name': user.name, 'email': user.email},
            'statistics': {
                'total_tasks': len(tasks),
                **by_status,
                'overdue': sum(task.is_overdue() for task in tasks),
                'high_priority': sum(task.priority <= HIGH_PRIORITY_MAX for task in tasks),
                'completion_rate': completion_rate(by_status[STATUS_DONE], len(tasks)),
            },
        }
