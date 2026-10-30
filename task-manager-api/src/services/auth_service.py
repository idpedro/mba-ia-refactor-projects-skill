"""Tokens de autenticação assinados com SECRET_KEY (substituem o token adivinhável antigo, decisão 4)."""
from itsdangerous import BadSignature, URLSafeTimedSerializer

_SALT = "auth-token"


class AuthService:
    def __init__(self, secret_key, max_age):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=_SALT)
        self._max_age = max_age

    def issue_token(self, user):
        return self._serializer.dumps({"user_id": user.id})

    def user_id_from_token(self, token):
        """Retorna o id do usuário ou None se o token for inválido/expirado."""
        try:
            return self._serializer.loads(token, max_age=self._max_age)["user_id"]
        except (BadSignature, KeyError, TypeError):
            return None
