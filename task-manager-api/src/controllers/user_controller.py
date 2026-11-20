import logging

from sqlalchemy.exc import IntegrityError

from src.constants import ROLE_USER
from src.controllers.validators import validate_login, validate_new_user, validate_user_update
from src.database import db
from src.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from src.models import Task, User

logger = logging.getLogger(__name__)

# Formato reduzido de task devolvido por GET /users/<id>/tasks.
USER_TASK_FIELDS = ('id', 'title', 'description', 'status', 'priority', 'created_at', 'due_date')
ADMIN_ONLY_FIELDS = ('role', 'active')


class UserController:
    def __init__(self, auth_service):
        self._auth = auth_service

    def list(self):
        return [
            {**user.to_dict(), 'task_count': task_count}
            for user, task_count in User.list_with_task_counts()
        ]

    def get(self, user_id):
        user = self._existing(user_id)
        data = user.to_dict()
        data['tasks'] = [task.to_dict() for task in Task.list_all(owner_id=user_id)]
        return data

    def tasks_of(self, user_id):
        self._existing(user_id)
        return [
            task.to_dict(include_overdue=True, fields=USER_TASK_FIELDS)
            for task in Task.list_all(owner_id=user_id)
        ]

    def create(self, actor, data):
        fields = validate_new_user(data)
        if actor is None or not actor.is_admin():
            fields['role'] = ROLE_USER  # cadastro público nunca escolhe o próprio role
        if User.email_taken(fields['email']):
            raise ConflictError('Email já cadastrado')

        user = User(name=fields['name'], email=fields['email'], role=fields['role'])
        user.set_password(fields['password'])
        db.session.add(user)
        self._commit_unique_email()
        logger.info('Usuário criado: %s - %s', user.id, user.name)
        return user.to_dict()

    def update(self, actor, user_id, data):
        user = self._existing(user_id)
        fields = validate_user_update(data)
        if not actor.is_admin() and any(field in fields for field in ADMIN_ONLY_FIELDS):
            raise ForbiddenError('Apenas administradores alteram role ou status')
        if 'email' in fields and User.email_taken(fields['email'], exclude_id=user_id):
            raise ConflictError('Email já cadastrado')

        password = fields.pop('password', None)
        for name, value in fields.items():
            setattr(user, name, value)
        if password is not None:
            user.set_password(password)
        self._commit_unique_email()
        return user.to_dict()

    def delete(self, user_id):
        user = self._existing(user_id)
        Task.delete_for_user(user_id)
        db.session.delete(user)
        db.session.commit()  # tasks e usuário saem na mesma transação
        logger.info('Usuário deletado: %s', user_id)
        return {'message': 'Usuário deletado com sucesso'}

    def login(self, data):
        email, password = validate_login(data)
        user = User.find_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError('Credenciais inválidas')
        if not user.active:
            raise ForbiddenError('Usuário inativo')
        if user.has_legacy_password():
            user.set_password(password)
            db.session.commit()
            logger.info('Senha de %s migrada para scrypt', user.email)
        return {
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'token': self._auth.issue_token(user.id),
        }

    @staticmethod
    def _existing(user_id):
        user = User.get(user_id)
        if user is None:
            raise NotFoundError('Usuário não encontrado')
        return user

    @staticmethod
    def _commit_unique_email():
        try:
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise ConflictError('Email já cadastrado') from error
