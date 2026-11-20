import logging

from src.controllers.validators import validar_login, validar_usuario
from src.errors import NotFoundError, UnauthorizedError

logger = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model):
        self.usuarios = usuario_model

    def listar(self):
        return self.usuarios.listar()

    def obter(self, usuario_id):
        usuario = self.usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        usuario = validar_usuario(dados)
        usuario_id = self.usuarios.criar(usuario["nome"], usuario["email"], usuario["senha"])
        logger.info("Usuário criado id=%s", usuario_id)
        return usuario_id

    def login(self, dados):
        email, senha = validar_login(dados)
        usuario = self.usuarios.autenticar(email, senha)
        if usuario is None:
            logger.info("Login falhou")
            raise UnauthorizedError("Email ou senha inválidos")
        logger.info("Login bem-sucedido usuario_id=%s", usuario["id"])
        return usuario
