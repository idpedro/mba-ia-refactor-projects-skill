import logging

from src.controllers import validators
from src.database import db, utcnow
from src.middlewares.error_handler import NotFoundError

logger = logging.getLogger(__name__)

TASK_NOT_FOUND = "Task não encontrada"
USER_NOT_FOUND = "Usuário não encontrado"
CATEGORY_NOT_FOUND = "Categoria não encontrada"


class TaskController:
    def __init__(self, task_model, user_model, category_model, report_service, notification_service):
        self.tasks = task_model
        self.users = user_model
        self.categories = category_model
        self.reports = report_service
        self.notifications = notification_service

    # ---- leitura -------------------------------------------------------------
    def list_tasks(self):
        result = []
        for task in self.tasks.all_with_relations():
            data = task.to_dict(include_overdue=True)
            data["user_name"] = task.user.name if task.user else None
            data["category_name"] = task.category.name if task.category else None
            result.append(data)
        return result

    def get_task(self, task_id):
        return self._find(task_id).to_dict(include_overdue=True)

    def search(self, args):
        filters = validators.parse_search_filters(args)
        return [task.to_dict() for task in self.tasks.search(**filters)]

    def stats(self):
        return self.reports.task_stats()

    # ---- escrita -------------------------------------------------------------
    def create_task(self, data):
        fields = validators.validate_new_task(data, self._check_refs)
        task = self.tasks(**fields)
        db.session.add(task)
        db.session.commit()
        logger.info("Task criada id=%s", task.id)
        self._notify_assignee(task)
        return task.to_dict()

    def update_task(self, task_id, data):
        task = self._find(task_id)
        changes = validators.validate_task_changes(data, self._check_refs)
        previous_user_id = task.user_id
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = utcnow()
        db.session.commit()
        logger.info("Task atualizada id=%s", task.id)
        if task.user_id != previous_user_id:
            self._notify_assignee(task)
        return task.to_dict()

    def delete_task(self, task_id):
        task = self._find(task_id)
        db.session.delete(task)
        db.session.commit()
        logger.info("Task deletada id=%s", task_id)

    # ---- apoio ---------------------------------------------------------------
    def _find(self, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError(TASK_NOT_FOUND)
        return task

    def _check_refs(self, user_id, category_id):
        if user_id and self.users.get(user_id) is None:
            raise NotFoundError(USER_NOT_FOUND)
        if category_id and self.categories.get(category_id) is None:
            raise NotFoundError(CATEGORY_NOT_FOUND)

    def _notify_assignee(self, task):
        if task.user_id:
            self.notifications.notify_task_assigned(self.users.get(task.user_id), task)
