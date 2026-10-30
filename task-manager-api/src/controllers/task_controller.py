import logging

from src.controllers.validators import parse_optional_int, validate_task
from src.database import utcnow
from src.errors import ForbiddenError, NotFoundError
from src.models import category_model, task_model, user_model
from src.models.task_model import Task

logger = logging.getLogger(__name__)


class TaskController:
    def __init__(self, notification_service, report_service):
        self.notifications = notification_service
        self.reports = report_service

    def list_all(self):
        result = []
        for task in task_model.list_tasks_with_relations():
            data = task.to_dict(include_overdue=True)
            data["user_name"] = task.user.name if task.user else None
            data["category_name"] = task.category.name if task.category else None
            result.append(data)
        return result

    def get(self, task_id):
        return self._find(task_id).to_dict(include_overdue=True)

    def search(self, args):
        tasks = task_model.search_tasks(
            text=args.get("q", ""),
            status=args.get("status", ""),
            priority=parse_optional_int(args.get("priority"), "Prioridade inválida"),
            user_id=parse_optional_int(args.get("user_id"), "user_id inválido"),
        )
        return [task.to_dict() for task in tasks]

    def stats(self):
        return self.reports.task_stats()

    def create(self, data, actor):
        fields = validate_task(data)
        self._check_assignment(fields["user_id"], actor)
        self._check_references(fields)

        task = Task(**fields)
        task_model.save(task)
        logger.info("Task criada id=%s", task.id)
        self._notify_assignment(task)
        return task.to_dict()

    def update(self, task_id, data, actor):
        task = self._find(task_id)
        self._check_owner(task, actor)
        fields = validate_task(data, partial=True)
        if "user_id" in fields:
            self._check_assignment(fields["user_id"], actor)
        self._check_references(fields)

        reassigned = "user_id" in fields and fields["user_id"] and fields["user_id"] != task.user_id
        for name, value in fields.items():
            setattr(task, name, value)
        task.updated_at = utcnow()
        task_model.save(task)
        logger.info("Task atualizada id=%s", task.id)
        if reassigned:
            self._notify_assignment(task)
        return task.to_dict()

    def delete(self, task_id, actor):
        task = self._find(task_id)
        self._check_owner(task, actor)
        task_model.delete(task)
        logger.info("Task deletada id=%s", task_id)

    def _find(self, task_id):
        task = task_model.get_task(task_id)
        if task is None:
            raise NotFoundError("Task não encontrada")
        return task

    @staticmethod
    def _check_owner(task, actor):
        if not actor.is_admin() and task.user_id != actor.id:
            raise ForbiddenError("Acesso negado")

    @staticmethod
    def _check_assignment(user_id, actor):
        if user_id is not None and user_id != actor.id and not actor.is_admin():
            raise ForbiddenError("Apenas administradores atribuem tasks a outros usuários")

    @staticmethod
    def _check_references(fields):
        if fields.get("user_id") and user_model.get_user(fields["user_id"]) is None:
            raise NotFoundError("Usuário não encontrado")
        if fields.get("category_id") and category_model.get_category(fields["category_id"]) is None:
            raise NotFoundError("Categoria não encontrada")

    def _notify_assignment(self, task):
        if task.user is not None:
            self.notifications.notify_task_assigned(task.user, task)
