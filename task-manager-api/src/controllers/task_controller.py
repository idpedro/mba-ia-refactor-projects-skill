import logging

from src.config.settings import DEFAULT_PRIORITY, TASK_STATUS_PENDING
from src.controllers.validators import parse_search_args, validate_task_payload
from src.database import utcnow
from src.errors import ForbiddenError, NotFoundError

logger = logging.getLogger(__name__)


class TaskController:
    def __init__(self, tasks, users, categories, report_service):
        self.tasks = tasks
        self.users = users
        self.categories = categories
        self.reports = report_service

    def list(self):
        return [task.to_listing_dict() for task in self.tasks.list_with_relations()]

    def get(self, task_id):
        return self._get_or_404(task_id).to_dict(include_overdue=True)

    def create(self, data):
        fields = validate_task_payload(data, creating=True)
        self._check_references(fields)
        fields.setdefault('description', '')
        fields.setdefault('status', TASK_STATUS_PENDING)
        fields.setdefault('priority', DEFAULT_PRIORITY)
        task = self.tasks(**fields)
        task.save()
        logger.info('Task criada id=%s title=%s', task.id, task.title)
        return task.to_dict()

    def update(self, task_id, data, actor):
        task = self._get_or_404(task_id)
        self._ensure_can_modify(task, actor)
        fields = validate_task_payload(data, creating=False)
        self._check_references(fields)
        for name, value in fields.items():
            setattr(task, name, value)
        task.updated_at = utcnow()
        task.save()
        logger.info('Task atualizada id=%s', task.id)
        return task.to_dict()

    def delete(self, task_id, actor):
        task = self._get_or_404(task_id)
        self._ensure_can_modify(task, actor)
        task.delete()
        logger.info('Task deletada id=%s', task_id)
        return {'message': 'Task deletada com sucesso'}

    def search(self, args):
        filters = parse_search_args(args)
        return [task.to_dict() for task in self.tasks.search(**filters)]

    def stats(self):
        return self.reports.task_stats()

    def _get_or_404(self, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError('Task não encontrada')
        return task

    def _check_references(self, fields):
        if fields.get('user_id') and self.users.get(fields['user_id']) is None:
            raise NotFoundError('Usuário não encontrado')
        if fields.get('category_id') and self.categories.get(fields['category_id']) is None:
            raise NotFoundError('Categoria não encontrada')

    @staticmethod
    def _ensure_can_modify(task, actor):
        if not (actor.is_admin() or task.user_id == actor.id):
            raise ForbiddenError('Acesso negado')
