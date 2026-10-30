from src.controllers.validators import validar_pedido, validar_status
from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO


class PedidoController:
    def __init__(self, pedido_model, notification_service):
        self.pedidos = pedido_model
        self.notifications = notification_service

    def criar(self, dados):
        pedido = validar_pedido(dados)
        resultado = self.pedidos.criar(pedido["usuario_id"], pedido["itens"])
        self.notifications.pedido_criado(resultado["pedido_id"], pedido["usuario_id"])
        return resultado

    def listar_todos(self):
        return self.pedidos.listar()

    def listar_do_usuario(self, usuario_id):
        return self.pedidos.listar(usuario_id=usuario_id)

    def atualizar_status(self, pedido_id, dados):
        novo_status = validar_status(dados)
        self.pedidos.atualizar_status(pedido_id, novo_status)
        if novo_status == STATUS_APROVADO:
            self.notifications.pedido_aprovado(pedido_id)
        elif novo_status == STATUS_CANCELADO:
            self.notifications.pedido_cancelado(pedido_id)
