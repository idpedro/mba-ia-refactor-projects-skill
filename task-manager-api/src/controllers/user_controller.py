import logging

from src.controllers.validators import validate_login, validate_new_user, validate_user_update
from src.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from src.models import task_model, user_model
from src.models.task_model import Task
from src.models.user_model import ROLE_USER, User

logger = logging.getLogger(__name__)

ADMIN_ONLY_FIELDS = ("role", "active")


class UserController:
    def list_all(self):
        task_counts = task_model.count_tasks_by(Task.user_id)
        result = []
        for user in user_model.list_users():
            data = user.to_dict()
            data["task_count"] = task_counts.get(user.id, 0)
            result.append(data)
        return result

    def get(self, user_id):
        data = self._find(user_id).to_dict()
        data["tasks"] = [task.to_dict() for task in task_model.list_tasks_by_user(user_id)]
        return data

    def find(self, user_id):
        return self._find(user_id)

    def tasks(self, user_id):
        self._find(user_id)
        return [task.to_summary_dict() for task in task_model.list_tasks_by_user(user_id)]

    def create(self, data, actor=None):
        fields = validate_new_user(data)
        if user_model.get_user_by_email(fields["email"]):
            raise ConflictError("Email já cadastrado")
        # Só um admin autenticado escolhe o role; cadastro público sempre cria "user".
        role = fields["role"] if actor is not None and actor.is_admin() else ROLE_USER

        user = User(name=fields["name"], email=fields["email"], role=role)
        user.set_password(fields["password"])
        user_model.save(user)
        logger.info("Usuário criado id=%s", user.id)
        return user.to_dict()

    def update(self, user_id, data, actor):
        user = self._find(user_id)
        fields = validate_user_update(data)
        if not actor.is_admin() and any(name in fields for name in ADMIN_ONLY_FIELDS):
            raise ForbiddenError("Apenas administradores alteram role ou active")
        if "email" in fields:
            existing = user_model.get_user_by_email(fields["email"])
            if existing and existing.id != user_id:
                raise ConflictError("Email já cadastrado")

        password = fields.pop("password", None)
        for name, value in fields.items():
            setattr(user, name, value)
        if password is not None:
            user.set_password(password)
        user_model.save(user)
        return user.to_dict()

    def delete(self, user_id):
        user_model.delete_with_tasks(self._find(user_id))
        logger.info("Usuário deletado id=%s", user_id)

    def authenticate(self, data):
        email, password = validate_login(data)
        user = user_model.get_user_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError("Credenciais inválidas")
        if not user.active:
            raise ForbiddenError("Usuário inativo")
        return user

    @staticmethod
    def _find(user_id):
        user = user_model.get_user(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user
