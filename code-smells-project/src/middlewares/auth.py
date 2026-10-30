from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.errors import ForbiddenError, UnauthorizedError
from src.models.usuario_model import TIPO_ADMIN


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")


def issue_token(usuario_id):
    return _serializer().dumps({"uid": usuario_id})


def _usuario_atual():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedError("Token ausente")
    try:
        dados = _serializer().loads(header[7:], max_age=current_app.config["TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError("Token inválido")
    usuario = current_app.extensions["usuario_model"].buscar_por_id(dados["uid"])
    if usuario is None:
        raise UnauthorizedError("Token inválido")
    return usuario


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _usuario_atual()
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _usuario_atual()
        if g.current_user["tipo"] != TIPO_ADMIN:
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)
    return wrapper


def require_self_or_admin(param):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = _usuario_atual()
            if g.current_user["id"] != kwargs[param] and g.current_user["tipo"] != TIPO_ADMIN:
                raise ForbiddenError("Acesso negado")
            return view(*args, **kwargs)
        return wrapper
    return decorator
