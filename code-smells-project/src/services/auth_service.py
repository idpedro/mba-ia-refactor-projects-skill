import logging

from werkzeug.security import check_password_hash, generate_password_hash

from src.errors import UnauthorizedError

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, usuario_model):
        self.usuarios = usuario_model

    def cadastrar(self, nome, email, senha):
        # O papel nunca vem do request: todo cadastro público é cliente.
        usuario_id = self.usuarios.criar(nome, email, generate_password_hash(senha))
        logger.info("Usuário criado id=%s", usuario_id)
        return usuario_id

    def autenticar(self, email, senha):
        row = self.usuarios.buscar_credenciais(email)
        if row is None or not check_password_hash(row["senha"] or "", senha):
            logger.info("Login falhou")
            raise UnauthorizedError("Email ou senha inválidos")
        logger.info("Login bem-sucedido id=%s", row["id"])
        return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
