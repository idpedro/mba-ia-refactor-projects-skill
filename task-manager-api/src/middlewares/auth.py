"""Tokens assinados (itsdangerous) e guards de rota. Sempre ativos: não há flag para desligar."""
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.errors import ForbiddenError, UnauthorizedError
from src.models import user_model

BEARER_PREFIX = "Bearer "


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")


def issue_token(user_id):
    return _serializer().dumps({"uid": user_id})


def _token_user(token):
    try:
        data = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError("Token inválido")
    user = user_model.get_user(data.get("uid"))
    if user is None:
        raise UnauthorizedError("Token inválido")
    if not user.active:
        raise ForbiddenError("Usuário inativo")
    return user


def current_user(optional=False):
    header = request.headers.get("Authorization", "")
    if not header:
        if optional:
            return None
        raise UnauthorizedError("Token ausente")
    if not header.startswith(BEARER_PREFIX):
        raise UnauthorizedError("Token inválido")
    return _token_user(header[len(BEARER_PREFIX):])


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = current_user()
        return view(*args, **kwargs)
    return wrapper


def optional_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = current_user(optional=True)
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = current_user()
        if not g.current_user.is_admin():
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)
    return wrapper


def require_self_or_admin(param):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = current_user()
            if g.current_user.id != kwargs[param] and not g.current_user.is_admin():
                raise ForbiddenError("Acesso negado")
            return view(*args, **kwargs)
        return wrapper
    return decorator
