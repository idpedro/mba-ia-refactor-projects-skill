"""Autenticação por token Bearer assinado (itsdangerous), sempre ativa."""
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.errors import ForbiddenError, UnauthorizedError
from src.models.constants import TIPO_ADMIN


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")


def issue_token(usuario_id):
    return _serializer().dumps({"uid": usuario_id})


def is_admin(usuario):
    return usuario["tipo"] == TIPO_ADMIN


def _usuario_atual():
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        raise UnauthorizedError("Token ausente")
    try:
        dados = _serializer().loads(cabecalho[len("Bearer "):], max_age=current_app.config["TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError("Token inválido") from None
    usuario = current_app.extensions["usuario_model"].buscar_por_id(dados.get("uid"))
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
        if not is_admin(g.current_user):
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)
    return wrapper


def require_self_or_admin(param):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = _usuario_atual()
            if g.current_user["id"] != kwargs[param] and not is_admin(g.current_user):
                raise ForbiddenError("Acesso negado")
            return view(*args, **kwargs)
        return wrapper
    return decorator


def owner_for(ator, dono_solicitado):
    """O dono de um registro vem do token; só admin escolhe outro dono."""
    if dono_solicitado is None:
        return ator["id"]
    if is_admin(ator):
        return dono_solicitado
    if dono_solicitado != ator["id"]:
        raise ForbiddenError("Apenas administradores criam pedidos para outros usuários")
    return ator["id"]
