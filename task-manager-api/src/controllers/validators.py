"""Validação única por entidade: create e update passam pelas mesmas regras e mensagens."""
import re
from datetime import datetime

from src.errors import ValidationError
from src.models.task_model import (
    DEFAULT_PRIORITY, MAX_PRIORITY, MAX_TITLE_LENGTH, MIN_PRIORITY, MIN_TITLE_LENGTH,
    STATUS_PENDING, VALID_STATUSES,
)
from src.models.user_model import ROLE_USER, VALID_ROLES

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
MIN_PASSWORD_LENGTH = 4
DATE_FORMAT = "%Y-%m-%d"


def require_body(data):
    if not isinstance(data, dict) or not data:
        raise ValidationError("Dados inválidos")
    return data


def parse_optional_int(value, message):
    """Aceita int ou string numérica; None/'' viram None."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValidationError(message)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(message)


def _title(value):
    if not value:
        raise ValidationError("Título é obrigatório")
    if not isinstance(value, str):
        raise ValidationError("Título inválido")
    if len(value) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(value) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return value


def _status(value):
    if value not in VALID_STATUSES:
        raise ValidationError("Status inválido")
    return value


def _priority(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("Prioridade inválida")
    if not MIN_PRIORITY <= value <= MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return value


def _due_date(value):
    if not value:
        return None
    if not isinstance(value, str):
        raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")


def _tags(value):
    if not value:
        return None
    if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
        return ",".join(value)
    if isinstance(value, str):
        return value
    raise ValidationError("Tags inválidas")


def validate_task(data, partial=False):
    """Retorna só os campos presentes (partial) ou todos com defaults (create)."""
    require_body(data)
    if not partial:
        data = {
            "description": "", "status": STATUS_PENDING, "priority": DEFAULT_PRIORITY,
            "user_id": None, "category_id": None, "due_date": None, "tags": None, **data,
        }
        data.setdefault("title", None)

    clean = {}
    if "title" in data:
        clean["title"] = _title(data["title"])
    if "description" in data:
        clean["description"] = data["description"]
    if "status" in data:
        clean["status"] = _status(data["status"])
    if "priority" in data:
        clean["priority"] = _priority(data["priority"])
    if "user_id" in data:
        clean["user_id"] = parse_optional_int(data["user_id"], "Usuário inválido")
    if "category_id" in data:
        clean["category_id"] = parse_optional_int(data["category_id"], "Categoria inválida")
    if "due_date" in data:
        clean["due_date"] = _due_date(data["due_date"])
    if "tags" in data:
        clean["tags"] = _tags(data["tags"])
    return clean


def _email(value):
    if not isinstance(value, str) or not EMAIL_PATTERN.match(value):
        raise ValidationError("Email inválido")
    return value


def _role(value):
    if value not in VALID_ROLES:
        raise ValidationError("Role inválido")
    return value


def validate_new_user(data):
    require_body(data)
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not name or not isinstance(name, str):
        raise ValidationError("Nome é obrigatório")
    if not email:
        raise ValidationError("Email é obrigatório")
    if not password:
        raise ValidationError("Senha é obrigatória")
    _email(email)
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres")
    return {"name": name, "email": email, "password": password, "role": _role(data.get("role", ROLE_USER))}


def validate_user_update(data):
    require_body(data)
    clean = {}
    if "name" in data:
        if not data["name"] or not isinstance(data["name"], str):
            raise ValidationError("Nome é obrigatório")
        clean["name"] = data["name"]
    if "email" in data:
        clean["email"] = _email(data["email"])
    if "password" in data:
        if not isinstance(data["password"], str) or len(data["password"]) < MIN_PASSWORD_LENGTH:
            raise ValidationError("Senha muito curta")
        clean["password"] = data["password"]
    if "role" in data:
        clean["role"] = _role(data["role"])
    if "active" in data:
        if not isinstance(data["active"], bool):
            raise ValidationError("Campo active deve ser booleano")
        clean["active"] = data["active"]
    return clean


def validate_login(data):
    require_body(data)
    email, password = data.get("email"), data.get("password")
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError("Email e senha são obrigatórios")
    return email, password


def _color(value):
    if not isinstance(value, str) or not COLOR_PATTERN.match(value):
        raise ValidationError("Cor inválida. Use #RRGGBB")
    return value


def validate_category(data, partial=False):
    require_body(data)
    clean = {}
    if not partial or "name" in data:
        if not data.get("name") or not isinstance(data.get("name"), str):
            raise ValidationError("Nome é obrigatório")
        clean["name"] = data["name"]
    if "description" in data or not partial:
        clean["description"] = data.get("description", "")
    if "color" in data:
        clean["color"] = _color(data["color"])
    return clean
