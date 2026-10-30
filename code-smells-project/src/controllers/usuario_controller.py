import logging

from src.controllers.validators import validar_login, validar_usuario
from src.errors import NotFoundError, UnauthorizedError

logger = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model):
        self.usuarios = usuario_model

    def listar(self):
        return self.usuarios.listar()

    def buscar(self, usuario_id):
        usuario = self.usuarios.buscar_por_id(usuario_id)
        if not usuario:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        usuario = validar_usuario(dados)
        usuario_id = self.usuarios.criar(**usuario)
        logger.info("Usuario criado id=%s", usuario_id)
        return usuario_id

    def login(self, dados):
        credenciais = validar_login(dados)
        usuario = self.usuarios.autenticar(credenciais["email"], credenciais["senha"])
        if not usuario:
            logger.info("Login falhou")
            raise UnauthorizedError("Email ou senha inválidos")
        logger.info("Login bem-sucedido id=%s", usuario["id"])
        return usuario
