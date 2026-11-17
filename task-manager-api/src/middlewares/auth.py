from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.errors import ForbiddenError, UnauthorizedError

BEARER_PREFIX = 'Bearer '


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='auth')


def issue_token(user_id):
    return _serializer().dumps({'uid': user_id})


def authenticate(required=True):
    """Resolve the bearer token to a User. Returns None for an anonymous call when not required."""
    header = request.headers.get('Authorization', '')
    if not header:
        if required:
            raise UnauthorizedError('Token ausente')
        return None
    if not header.startswith(BEARER_PREFIX):
        raise UnauthorizedError('Token inválido')
    try:
        data = _serializer().loads(header[len(BEARER_PREFIX):], max_age=current_app.config['TOKEN_MAX_AGE'])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError('Token inválido')
    user = current_app.extensions['user_model'].get(data.get('uid'))
    if user is None or not user.active:
        raise UnauthorizedError('Token inválido')
    return user


def optional_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = authenticate(required=False)
        return view(*args, **kwargs)
    return wrapper


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = authenticate()
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = authenticate()
        if not g.current_user.is_admin():
            raise ForbiddenError('Acesso restrito a administradores')
        return view(*args, **kwargs)
    return wrapper


def require_self_or_admin(param):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = authenticate()
            if g.current_user.id != kwargs[param] and not g.current_user.is_admin():
                raise ForbiddenError('Acesso negado')
            return view(*args, **kwargs)
        return wrapper
    return decorator
