import logging

from src.config.settings import ROLE_USER
from src.controllers.validators import validate_login_payload, validate_user_payload
from src.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError

logger = logging.getLogger(__name__)


class UserController:
    def __init__(self, users, tasks):
        self.users = users
        self.tasks = tasks

    def list(self):
        counts = self.users.task_counts()
        return [dict(user.to_dict(), task_count=counts.get(user.id, 0)) for user in self.users.list_all()]

    def get(self, user_id):
        user = self._get_or_404(user_id)
        data = user.to_dict()
        data['tasks'] = [task.to_dict() for task in self.tasks.for_user(user_id)]
        return data

    def create(self, data, actor):
        fields = validate_user_payload(data, creating=True)
        if self.users.get_by_email(fields['email']):
            raise ConflictError('Email já cadastrado')
        role = fields.get('role', ROLE_USER)
        if role != ROLE_USER and not (actor and actor.is_admin()):
            raise ForbiddenError('Apenas administradores podem definir o role')
        user = self.users(name=fields['name'], email=fields['email'], role=role)
        user.set_password(fields['password'])
        user.save()
        logger.info('Usuário criado id=%s', user.id)
        return user.to_dict()

    def update(self, user_id, data, actor):
        user = self._get_or_404(user_id)
        fields = validate_user_payload(data, creating=False)

        if 'email' in fields and fields['email'] != user.email:
            existing = self.users.get_by_email(fields['email'])
            if existing and existing.id != user.id:
                raise ConflictError('Email já cadastrado')
        privileged = {name for name in ('role', 'active') if name in fields and fields[name] != getattr(user, name)}
        if privileged and not actor.is_admin():
            raise ForbiddenError('Apenas administradores podem alterar role ou active')

        for name in ('name', 'email', 'role', 'active'):
            if name in fields:
                setattr(user, name, fields[name])
        if 'password' in fields:
            user.set_password(fields['password'])
        user.save()
        return user.to_dict()

    def delete(self, user_id):
        user = self._get_or_404(user_id)
        user.delete_with_tasks()
        logger.info('Usuário deletado id=%s', user_id)
        return {'message': 'Usuário deletado com sucesso'}

    def tasks_of(self, user_id):
        self._get_or_404(user_id)
        return [task.to_summary_dict() for task in self.tasks.for_user(user_id)]

    def login(self, data):
        email, password = validate_login_payload(data)
        user = self.users.get_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError('Credenciais inválidas')
        if not user.active:
            raise ForbiddenError('Usuário inativo')
        if user.needs_rehash():
            user.set_password(password)
            user.save()
        return user

    def _get_or_404(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError('Usuário não encontrado')
        return user
