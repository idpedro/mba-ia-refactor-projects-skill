"""Emissão e verificação de tokens assinados (itsdangerous, já incluso no Flask)."""
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.errors import UnauthorizedError


class AuthService:
    def __init__(self, secret_key, max_age):
        self._serializer = URLSafeTimedSerializer(secret_key, salt='auth')
        self._max_age = max_age

    def issue_token(self, user_id):
        return self._serializer.dumps({'uid': user_id})

    def user_id_from(self, token):
        try:
            data = self._serializer.loads(token, max_age=self._max_age)
        except BadSignature as error:  # inclui SignatureExpired
            raise UnauthorizedError('Token inválido') from error
        user_id = data.get('uid') if isinstance(data, dict) else None
        if not isinstance(user_id, int):
            raise UnauthorizedError('Token inválido')
        return user_id
