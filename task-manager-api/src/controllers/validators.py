import re
from datetime import datetime

from src.config.settings import (
    DATE_FORMAT,
    DEFAULT_CATEGORY_COLOR,
    MAX_CATEGORY_DESCRIPTION_LENGTH,
    MAX_CATEGORY_NAME_LENGTH,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    ROLES,
    TASK_STATUSES,
)
from src.errors import ValidationError

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')
COLOR_LENGTH = 7


def require_json(data):
    if not isinstance(data, dict) or not data:
        raise ValidationError('Dados inválidos')
    return data


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')


def _validate_priority(priority):
    if not _is_int(priority):
        raise ValidationError('Prioridade inválida')
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')


def _validate_reference(value, label):
    if value and not _is_int(value):
        raise ValidationError(f'{label} inválido')
    return value or None


def _parse_due_date(value, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValidationError(message)


def _normalize_tags(tags):
    if tags is None or isinstance(tags, str):
        return tags
    if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
        return ','.join(tags)
    raise ValidationError('Tags inválidas')


def validate_task_payload(data, creating):
    """Fields present in `data`, validated. Same rules for create and update."""
    data = require_json(data)
    fields = {}

    if creating and not data.get('title'):
        raise ValidationError('Título é obrigatório')
    if 'title' in data:
        _validate_title(data['title'])
        fields['title'] = data['title']

    if 'description' in data:
        if data['description'] is not None and not isinstance(data['description'], str):
            raise ValidationError('Descrição inválida')
        fields['description'] = data['description']

    if 'status' in data:
        if not isinstance(data['status'], str) or data['status'] not in TASK_STATUSES:
            raise ValidationError('Status inválido')
        fields['status'] = data['status']

    if 'priority' in data:
        _validate_priority(data['priority'])
        fields['priority'] = data['priority']

    if 'user_id' in data:
        fields['user_id'] = _validate_reference(data['user_id'], 'user_id')
    if 'category_id' in data:
        fields['category_id'] = _validate_reference(data['category_id'], 'category_id')

    if 'due_date' in data:
        if data['due_date']:
            message = 'Formato de data inválido. Use YYYY-MM-DD' if creating else 'Formato de data inválido'
            fields['due_date'] = _parse_due_date(data['due_date'], message)
        else:
            fields['due_date'] = None

    if 'tags' in data:
        fields['tags'] = _normalize_tags(data['tags'])

    return fields


def parse_search_args(args):
    filters = {'text': args.get('q', ''), 'status': args.get('status', '')}
    priority = args.get('priority', '')
    user_id = args.get('user_id', '')
    try:
        filters['priority'] = int(priority) if priority else None
    except ValueError:
        raise ValidationError('Prioridade inválida')
    try:
        filters['user_id'] = int(user_id) if user_id else None
    except ValueError:
        raise ValidationError('user_id inválido')
    return filters


def _validate_email(email):
    if not isinstance(email, str) or not EMAIL_PATTERN.match(email):
        raise ValidationError('Email inválido')


def _validate_role(role):
    if not isinstance(role, str) or role not in ROLES:
        raise ValidationError('Role inválido')


def _validate_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValidationError('Nome inválido')


def validate_user_payload(data, creating):
    data = require_json(data)
    fields = {}

    if creating:
        if not data.get('name'):
            raise ValidationError('Nome é obrigatório')
        if not data.get('email'):
            raise ValidationError('Email é obrigatório')
        if not data.get('password'):
            raise ValidationError('Senha é obrigatória')

    if 'name' in data:
        _validate_name(data['name'])
        fields['name'] = data['name']

    if 'email' in data:
        _validate_email(data['email'])
        fields['email'] = data['email']

    if 'password' in data:
        password = data['password']
        if not isinstance(password, str):
            raise ValidationError('Senha inválida')
        if len(password) < MIN_PASSWORD_LENGTH:
            message = 'Senha deve ter no mínimo 4 caracteres' if creating else 'Senha muito curta'
            raise ValidationError(message)
        fields['password'] = password

    if 'role' in data:
        _validate_role(data['role'])
        fields['role'] = data['role']

    if 'active' in data:
        if not isinstance(data['active'], bool):
            raise ValidationError('Campo active inválido')
        fields['active'] = data['active']

    return fields


def validate_login_payload(data):
    data = require_json(data)
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError('Credenciais inválidas')
    return email, password


def validate_category_payload(data, creating):
    data = require_json(data)
    fields = {}

    if creating and not data.get('name'):
        raise ValidationError('Nome é obrigatório')
    if 'name' in data:
        name = data['name']
        if not isinstance(name, str) or not name.strip() or len(name) > MAX_CATEGORY_NAME_LENGTH:
            raise ValidationError('Nome inválido')
        fields['name'] = name

    if 'description' in data:
        description = data['description']
        if description is not None and (
            not isinstance(description, str) or len(description) > MAX_CATEGORY_DESCRIPTION_LENGTH
        ):
            raise ValidationError('Descrição inválida')
        fields['description'] = description

    if 'color' in data:
        color = data['color']
        if not isinstance(color, str) or len(color) != COLOR_LENGTH or not color.startswith('#'):
            raise ValidationError('Cor inválida')
        fields['color'] = color

    if creating:
        fields.setdefault('description', '')
        fields.setdefault('color', DEFAULT_CATEGORY_COLOR)
    return fields
