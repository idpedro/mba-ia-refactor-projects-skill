"""Guards de autenticação. Sempre ativos: não há variável que os desligue."""
from functools import wraps

from flask import current_app, g, request

from src.errors import ForbiddenError, UnauthorizedError
from src.models import User

BEARER_PREFIX = 'Bearer '


def _user_from_header():
    header = request.headers.get('Authorization', '')
    if not header.startswith(BEARER_PREFIX):
        return None
    user_id = current_app.extensions['auth_service'].user_id_from(header[len(BEARER_PREFIX):])
    user = User.get(user_id)
    if user is None:
        raise UnauthorizedError('Token inválido')
    if not user.active:
        raise ForbiddenError('Usuário inativo')
    return user


def current_user():
    user = _user_from_header()
    if user is None:
        raise UnauthorizedError('Token ausente')
    return user


def optional_user():
    """Usuário do token, se houver; rotas públicas usam para reconhecer o admin."""
    return _user_from_header()


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = current_user()
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = current_user()
        if not g.current_user.is_admin():
            raise ForbiddenError('Acesso restrito a administradores')
        return view(*args, **kwargs)
    return wrapper


def require_self_or_admin(param):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = current_user()
            if g.current_user.id != kwargs[param] and not g.current_user.is_admin():
                raise ForbiddenError('Acesso negado')
            return view(*args, **kwargs)
        return wrapper
    return decorator
