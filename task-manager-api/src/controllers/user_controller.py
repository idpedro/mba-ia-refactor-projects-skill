import logging

from src.controllers import validators
from src.database import db
from src.middlewares.error_handler import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from src.models.user_model import DEFAULT_ROLE

logger = logging.getLogger(__name__)

USER_NOT_FOUND = "Usuário não encontrado"
EMAIL_TAKEN = "Email já cadastrado"
INVALID_CREDENTIALS = "Credenciais inválidas"


class UserController:
    def __init__(self, user_model, task_model, auth_service):
        self.users = user_model
        self.tasks = task_model
        self.auth = auth_service

    # ---- leitura -------------------------------------------------------------
    def list_users(self):
        task_counts = self.tasks.count_by_user()
        return [{**user.to_dict(), "task_count": task_counts.get(user.id, 0)} for user in self.users.all()]

    def get_user(self, user_id):
        user = self._find(user_id)
        return {**user.to_dict(), "tasks": [task.to_dict() for task in self.tasks.by_user(user_id)]}

    def list_user_tasks(self, user_id):
        self._find(user_id)
        return [task.to_summary_dict() for task in self.tasks.by_user(user_id)]

    # ---- escrita -------------------------------------------------------------
    def create_user(self, data):
        fields = validators.validate_new_user(data)
        if self.users.find_by_email(fields["email"]):
            raise ConflictError(EMAIL_TAKEN)
        user = self.users(name=fields["name"], email=fields["email"], role=DEFAULT_ROLE)
        user.set_password(fields["password"])
        db.session.add(user)
        db.session.commit()
        logger.info("Usuário criado id=%s", user.id)
        return user.to_dict()

    def update_user(self, user_id, data):
        user = self._find(user_id)
        changes = validators.validate_user_changes(data, lambda email: self._check_email_free(email, user_id))
        password = changes.pop("password", None)
        for field, value in changes.items():
            setattr(user, field, value)
        if password is not None:
            user.set_password(password)
        db.session.commit()
        return user.to_dict()

    def delete_user(self, user_id):
        user = self._find(user_id)
        self.tasks.delete_by_user(user_id)
        db.session.delete(user)
        db.session.commit()  # tasks e usuário na mesma transação
        logger.info("Usuário deletado id=%s", user_id)

    # ---- autenticação --------------------------------------------------------
    def login(self, data):
        email, password = validators.validate_credentials(data)
        user = self.users.find_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError(INVALID_CREDENTIALS)
        if not user.active:
            raise ForbiddenError("Usuário inativo")
        if user.needs_rehash():
            user.set_password(password)  # migra hash legado (decisão 2)
            db.session.commit()
        return {
            "message": "Login realizado com sucesso",
            "user": user.to_dict(),
            "token": self.auth.issue_token(user),
        }

    def authenticate(self, token):
        user_id = self.auth.user_id_from_token(token) if token else None
        user = self.users.get(user_id) if user_id else None
        if user is None or not user.active:
            raise UnauthorizedError("Token inválido ou ausente")
        return user

    def _check_email_free(self, email, user_id):
        existing = self.users.find_by_email(email)
        if existing and existing.id != user_id:
            raise ConflictError(EMAIL_TAKEN)

    def _find(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError(USER_NOT_FOUND)
        return user
