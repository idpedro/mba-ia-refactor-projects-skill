"""Validação de entrada: um validador por entidade, usado por create e update.

As mensagens são as mesmas da API original, para manter os corpos de erro do baseline.
"""
import re
from datetime import datetime

from src.middlewares.error_handler import ValidationError
from src.models.task_model import (
    DUE_DATE_FORMAT,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    TASK_STATUSES,
    Task,
)
from src.models.category_model import DEFAULT_COLOR
from src.models.user_model import EMAIL_PATTERN, MIN_PASSWORD_LENGTH, USER_ROLES

INVALID_DATA = "Dados inválidos"


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def require_payload(data):
    if not data or not isinstance(data, dict):
        raise ValidationError(INVALID_DATA)
    return data


# ---- tasks -------------------------------------------------------------------

def _check_title(title):
    if not isinstance(title, str):
        raise ValidationError("Título inválido")
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")


def _check_status(status):
    if status not in TASK_STATUSES:
        raise ValidationError("Status inválido")


def _check_priority(priority):
    if not _is_number(priority) or priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")


def _parse_due_date(value, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, DUE_DATE_FORMAT)
    except ValueError:
        raise ValidationError(message) from None


def validate_new_task(data, check_refs):
    """Regras de POST /tasks, na ordem original; `check_refs(user_id, category_id)` valida as FKs."""
    data = require_payload(data)
    title = data.get("title")
    if not title:
        raise ValidationError("Título é obrigatório")
    _check_title(title)

    fields = {
        "title": title,
        "description": data.get("description", ""),
        "status": data.get("status", "pending"),
        "priority": data.get("priority", 3),
        "user_id": data.get("user_id"),
        "category_id": data.get("category_id"),
    }
    _check_status(fields["status"])
    _check_priority(fields["priority"])
    check_refs(fields["user_id"], fields["category_id"])
    if data.get("due_date"):
        fields["due_date"] = _parse_due_date(data["due_date"], "Formato de data inválido. Use YYYY-MM-DD")
    if data.get("tags"):
        fields["tags"] = Task.join_tags(data["tags"])
    return fields


def validate_task_changes(data, check_refs):
    """Regras de PUT /tasks/<id>: só os campos presentes são validados e devolvidos."""
    data = require_payload(data)
    changes = {}
    if "title" in data:
        _check_title(data["title"])
        changes["title"] = data["title"]
    if "description" in data:
        changes["description"] = data["description"]
    if "status" in data:
        _check_status(data["status"])
        changes["status"] = data["status"]
    if "priority" in data:
        _check_priority(data["priority"])
        changes["priority"] = data["priority"]
    for key in ("user_id", "category_id"):
        if key in data:
            changes[key] = data[key]
    check_refs(changes.get("user_id"), changes.get("category_id"))
    if "due_date" in data:
        due = data["due_date"]
        changes["due_date"] = _parse_due_date(due, "Formato de data inválido") if due else None
    if "tags" in data:
        changes["tags"] = Task.join_tags(data["tags"])
    return changes


def parse_search_filters(args):
    filters = {"text": args.get("q", ""), "status": args.get("status", "")}
    for key, message in (("priority", "Prioridade inválida"), ("user_id", "user_id inválido")):
        raw = args.get(key, "")
        try:
            filters[key] = int(raw) if raw else None
        except ValueError:
            raise ValidationError(message) from None
    return filters


# ---- users -------------------------------------------------------------------

def _check_email(email):
    if not isinstance(email, str) or not re.match(EMAIL_PATTERN, email):
        raise ValidationError("Email inválido")


def _check_password_type(password):
    if not isinstance(password, str):
        raise ValidationError("Senha inválida")


def validate_new_user(data):
    """Regras de POST /users. `role` do corpo é ignorado (decisão 3)."""
    data = require_payload(data)
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not name:
        raise ValidationError("Nome é obrigatório")
    if not email:
        raise ValidationError("Email é obrigatório")
    if not password:
        raise ValidationError("Senha é obrigatória")
    if not isinstance(name, str):
        raise ValidationError("Nome inválido")
    _check_email(email)
    _check_password_type(password)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres")
    return {"name": name, "email": email, "password": password}


def validate_user_changes(data, check_email_free):
    """Regras de PUT /users/<id>, na ordem original; `check_email_free(email)` checa duplicidade."""
    data = require_payload(data)
    changes = {}
    if "name" in data:
        if not isinstance(data["name"], str):
            raise ValidationError("Nome inválido")
        changes["name"] = data["name"]
    if "email" in data:
        _check_email(data["email"])
        check_email_free(data["email"])
        changes["email"] = data["email"]
    if "password" in data:
        _check_password_type(data["password"])
        if len(data["password"]) < MIN_PASSWORD_LENGTH:
            raise ValidationError("Senha muito curta")
        changes["password"] = data["password"]
    if "role" in data:
        if data["role"] not in USER_ROLES:
            raise ValidationError("Role inválido")
        changes["role"] = data["role"]
    if "active" in data:
        if not isinstance(data["active"], bool):
            raise ValidationError("Campo active inválido")
        changes["active"] = data["active"]
    return changes


def validate_credentials(data):
    data = require_payload(data)
    email, password = data.get("email"), data.get("password")
    if not email or not password:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError("Email e senha são obrigatórios")
    return email, password


# ---- categories --------------------------------------------------------------

def validate_new_category(data):
    data = require_payload(data)
    name = data.get("name")
    if not name:
        raise ValidationError("Nome é obrigatório")
    if not isinstance(name, str):
        raise ValidationError("Nome inválido")
    return {
        "name": name,
        "description": data.get("description", ""),
        "color": data.get("color", DEFAULT_COLOR),
    }


def validate_category_changes(data):
    if not isinstance(data, dict):  # corpo `{}` continua aceito, como no original
        raise ValidationError(INVALID_DATA)
    changes = {}
    for key in ("name", "description", "color"):
        if key in data:
            if data[key] is not None and not isinstance(data[key], str):
                raise ValidationError(f"Campo {key} inválido")
            changes[key] = data[key]
    return changes
