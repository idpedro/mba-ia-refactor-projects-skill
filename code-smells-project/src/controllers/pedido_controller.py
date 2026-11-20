from src.controllers.validators import validar_pedido, validar_status
from src.errors import NotFoundError, ValidationError
from src.middlewares.auth import owner_for


class PedidoController:
    def __init__(self, pedido_model, usuario_model, notification_service, relatorio_service):
        self.pedidos = pedido_model
        self.usuarios = usuario_model
        self.notificacoes = notification_service
        self.relatorios = relatorio_service

    def criar(self, dados, ator):
        payload = validar_pedido(dados)
        dono = owner_for(ator, payload["usuario_id"])
        if dono != ator["id"] and self.usuarios.buscar_por_id(dono) is None:
            raise ValidationError("Usuário não encontrado")
        resultado = self.pedidos.criar(dono, payload["quantidades"])
        self.notificacoes.pedido_criado(resultado["pedido_id"], dono)
        return resultado

    def listar(self):
        return self.pedidos.listar()

    def listar_por_usuario(self, usuario_id):
        return self.pedidos.listar_por_usuario(usuario_id)

    def atualizar_status(self, pedido_id, dados):
        status = validar_status(dados)
        if not self.pedidos.atualizar_status(pedido_id, status):
            raise NotFoundError("Pedido não encontrado")
        self.notificacoes.status_alterado(pedido_id, status)

    def relatorio_vendas(self):
        return self.relatorios.vendas()
