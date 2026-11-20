"""Validação única de entrada por entidade, usada na criação e na atualização.

As mensagens são as que a API já devolvia; cada função devolve só os campos aceitos.
"""
import re
from datetime import datetime

from src.constants import (
    DATE_FORMAT,
    DEFAULT_COLOR,
    DEFAULT_PRIORITY,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    ROLE_USER,
    STATUS_PENDING,
    TASK_STATUSES,
    USER_ROLES,
)
from src.errors import ValidationError

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')
COLOR_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')


def require_body(data):
    if not isinstance(data, dict) or not data:
        raise ValidationError('Dados inválidos')
    return data


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_int_param(raw, message):
    """Inteiro de query string; vazio = sem filtro."""
    if raw in (None, ''):
        return None
    try:
        return int(raw)
    except ValueError as error:
        raise ValidationError(message) from error


def _optional_text(data, field, message):
    value = data.get(field)
    if value is not None and not isinstance(value, str):
        raise ValidationError(message)
    return value


def _optional_id(data, field, message):
    value = data.get(field)
    if value is not None and not is_int(value):
        raise ValidationError(message)
    return value or None


# ---------------------------------------------------------------- tasks

def _task_title(data, partial):
    title = data.get('title')
    if not partial and not title:
        raise ValidationError('Título é obrigatório')
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def _task_priority(value):
    if not is_int(value):
        raise ValidationError('Prioridade inválida')
    if not MIN_PRIORITY <= value <= MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')
    return value


def _task_due_date(value, partial):
    if not value:
        return None
    message = 'Formato de data inválido' if partial else 'Formato de data inválido. Use YYYY-MM-DD'
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError as error:
        raise ValidationError(message) from error


def _task_tags(value):
    if value is None or isinstance(value, str):
        return value or None
    if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
        return ','.join(value) or None
    raise ValidationError('Tags inválidas')


def validate_task(data, partial=False):
    """Campos válidos de uma task. `partial` = atualização (só o que veio no corpo)."""
    require_body(data)
    present = data.keys() if partial else (
        'title', 'description', 'status', 'priority', 'user_id', 'category_id', 'due_date', 'tags'
    )
    defaults = {} if partial else {'description': '', 'status': STATUS_PENDING, 'priority': DEFAULT_PRIORITY}
    source = {**defaults, **data}
    fields = {}
    if 'title' in present:
        fields['title'] = _task_title(source, partial)
    if 'description' in present:
        fields['description'] = _optional_text(source, 'description', 'Descrição inválida')
    if 'status' in present:
        if source.get('status') not in TASK_STATUSES:
            raise ValidationError('Status inválido')
        fields['status'] = source['status']
    if 'priority' in present:
        fields['priority'] = _task_priority(source.get('priority'))
    if 'user_id' in present:
        fields['user_id'] = _optional_id(source, 'user_id', 'Usuário inválido')
    if 'category_id' in present:
        fields['category_id'] = _optional_id(source, 'category_id', 'Categoria inválida')
    if 'due_date' in present:
        fields['due_date'] = _task_due_date(source.get('due_date'), partial)
    if 'tags' in present:
        fields['tags'] = _task_tags(source.get('tags'))
    return fields


# ---------------------------------------------------------------- users

def _user_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError('Nome é obrigatório')
    return value


def _user_email(value):
    if not isinstance(value, str) or not EMAIL_PATTERN.match(value):
        raise ValidationError('Email inválido')
    return value


def _user_password(value, short_message):
    if not isinstance(value, str):
        raise ValidationError('Senha inválida')
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(short_message)
    return value


def _user_role(value):
    if value not in USER_ROLES:
        raise ValidationError('Role inválido')
    return value


def validate_new_user(data):
    require_body(data)
    for field, message in (
        ('name', 'Nome é obrigatório'),
        ('email', 'Email é obrigatório'),
        ('password', 'Senha é obrigatória'),
    ):
        if not data.get(field):
            raise ValidationError(message)
    return {
        'name': _user_name(data['name']),
        'email': _user_email(data['email']),
        'password': _user_password(data['password'], 'Senha deve ter no mínimo 4 caracteres'),
        'role': _user_role(data.get('role', ROLE_USER)),
    }


def validate_user_update(data):
    require_body(data)
    fields = {}
    if 'name' in data:
        fields['name'] = _user_name(data['name'])
    if 'email' in data:
        fields['email'] = _user_email(data['email'])
    if 'password' in data:
        fields['password'] = _user_password(data['password'], 'Senha muito curta')
    if 'role' in data:
        fields['role'] = _user_role(data['role'])
    if 'active' in data:
        if not isinstance(data['active'], bool):
            raise ValidationError('Campo active inválido')
        fields['active'] = data['active']
    return fields


def validate_login(data):
    require_body(data)
    email, password = data.get('email'), data.get('password')
    if not (isinstance(email, str) and email and isinstance(password, str) and password):
        raise ValidationError('Email e senha são obrigatórios')
    return email, password


# ---------------------------------------------------------------- categories

def validate_category(data, partial=False):
    require_body(data)
    source = data if partial else {'description': '', 'color': DEFAULT_COLOR, **data}
    fields = {}
    if not partial or 'name' in source:
        fields['name'] = _user_name(source.get('name'))
    if 'description' in source:
        fields['description'] = _optional_text(source, 'description', 'Descrição inválida')
    if 'color' in source:
        color = source['color']
        if not isinstance(color, str) or not COLOR_PATTERN.match(color):
            raise ValidationError('Cor inválida')
        fields['color'] = color
    return fields
