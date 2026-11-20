import logging

from src.controllers.validators import parse_int_param, validate_task
from src.database import db
from src.errors import ForbiddenError, NotFoundError
from src.models import Category, Task, User
from src.models.base import utcnow

logger = logging.getLogger(__name__)


def visible_owner(actor):
    """Dono cujas tasks o ator enxerga: todas para o admin, só as próprias para os demais."""
    return None if actor.is_admin() else actor.id


class TaskController:
    def __init__(self, notification_service):
        self._notifications = notification_service

    # ------------------------------------------------------------ leitura

    def list(self, actor):
        tasks = Task.list_all(owner_id=visible_owner(actor), with_relations=True)
        return [task.to_dict(include_overdue=True, include_names=True) for task in tasks]

    def get(self, actor, task_id):
        return self._accessible_task(actor, task_id).to_dict(include_overdue=True)

    def search(self, actor, args):
        user_id = parse_int_param(args.get('user_id'), 'Usuário inválido')
        if not actor.is_admin():
            if user_id not in (None, actor.id):
                raise ForbiddenError('Acesso negado')
            user_id = actor.id
        tasks = Task.search(
            text=args.get('q', ''),
            status=args.get('status', ''),
            priority=parse_int_param(args.get('priority'), 'Prioridade inválida'),
            owner_id=user_id,
        )
        return [task.to_dict() for task in tasks]

    # ------------------------------------------------------------ escrita

    def create(self, actor, data):
        fields = validate_task(data, partial=False)
        fields['user_id'] = self._owner_for(actor, fields['user_id'])
        assignee = self._existing_user(fields['user_id'])
        self._ensure_category(fields['category_id'])

        task = Task(**fields)
        db.session.add(task)
        db.session.commit()
        logger.info('Task criada: %s - %s', task.id, task.title)
        if assignee is not None:
            self._notifications.notify_task_assigned(assignee, task)
        return task.to_dict()

    def update(self, actor, task_id, data):
        task = self._accessible_task(actor, task_id)
        fields = validate_task(data, partial=True)
        assignee = None
        if 'user_id' in fields:
            if not actor.is_admin() and fields['user_id'] != actor.id:
                raise ForbiddenError('Apenas administradores reatribuem tasks')
            assignee = self._existing_user(fields['user_id'])
            if fields['user_id'] == task.user_id:
                assignee = None
        if 'category_id' in fields:
            self._ensure_category(fields['category_id'])

        for name, value in fields.items():
            setattr(task, name, value)
        task.updated_at = utcnow()
        db.session.commit()
        logger.info('Task atualizada: %s', task.id)
        if assignee is not None:
            self._notifications.notify_task_assigned(assignee, task)
        return task.to_dict()

    def delete(self, actor, task_id):
        task = self._accessible_task(actor, task_id)
        db.session.delete(task)
        db.session.commit()
        logger.info('Task deletada: %s', task_id)
        return {'message': 'Task deletada com sucesso'}

    # ------------------------------------------------------------ regras

    @staticmethod
    def _accessible_task(actor, task_id):
        task = Task.get(task_id)
        if task is None:
            raise NotFoundError('Task não encontrada')
        if not actor.is_admin() and task.user_id != actor.id:
            raise ForbiddenError('Acesso negado')
        return task

    @staticmethod
    def _owner_for(actor, requested_owner_id):
        if actor.is_admin():
            return requested_owner_id
        if requested_owner_id not in (None, actor.id):
            raise ForbiddenError('Apenas administradores criam tasks para outros usuários')
        return actor.id

    @staticmethod
    def _existing_user(user_id):
        if user_id is None:
            return None
        user = User.get(user_id)
        if user is None:
            raise NotFoundError('Usuário não encontrado')
        return user

    @staticmethod
    def _ensure_category(category_id):
        if category_id is not None and Category.get(category_id) is None:
            raise NotFoundError('Categoria não encontrada')
