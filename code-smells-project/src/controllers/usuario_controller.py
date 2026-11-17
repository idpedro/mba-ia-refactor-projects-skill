from src.controllers.validators import validar_login, validar_usuario
from src.errors import NotFoundError


class UsuarioController:
    def __init__(self, usuario_model, auth_service):
        self.usuarios = usuario_model
        self.auth = auth_service

    def listar(self):
        return self.usuarios.listar()

    def obter(self, usuario_id):
        usuario = self.usuarios.buscar_por_id(usuario_id)
        if not usuario:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        return self.auth.cadastrar(**validar_usuario(dados))

    def login(self, dados):
        return self.auth.autenticar(**validar_login(dados))
