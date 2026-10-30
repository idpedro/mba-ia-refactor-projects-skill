"""Guarda de autenticação para rotas de escrita (decisão 4).

Desligada por padrão (`AUTH_REQUIRED=0`) para preservar o contrato atual; quando ligada,
exige `Authorization: Bearer <token>` emitido por POST /login.
"""
from functools import wraps

from flask import current_app, g, request

from src.middlewares.error_handler import ForbiddenError

_BEARER = "Bearer "


def build_auth_guards(user_controller):
    def _enabled():
        return current_app.config.get("AUTH_REQUIRED", False)

    def _current_user():
        header = request.headers.get("Authorization", "")
        token = header[len(_BEARER):] if header.startswith(_BEARER) else None
        return user_controller.authenticate(token)

    def require_auth(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if _enabled():
                g.current_user = _current_user()
            return view(*args, **kwargs)

        return wrapper

    def require_self_or_admin(view):
        """Para rotas /users/<user_id>: só o próprio usuário ou um admin."""
        @wraps(view)
        def wrapper(*args, **kwargs):
            if _enabled():
                user = _current_user()
                if user.id != kwargs.get("user_id") and not user.is_admin():
                    raise ForbiddenError("Acesso negado")
                body = request.get_json(silent=True)
                if isinstance(body, dict) and "role" in body and not user.is_admin():
                    raise ForbiddenError("Apenas administradores alteram roles")
                g.current_user = user
            return view(*args, **kwargs)

        return wrapper

    return require_auth, require_self_or_admin
