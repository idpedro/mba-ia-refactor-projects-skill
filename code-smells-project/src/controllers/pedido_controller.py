from src.controllers.validators import validar_pedido, validar_status


class PedidoController:
    def __init__(self, pedido_model, notification_service):
        self.pedidos = pedido_model
        self.notifications = notification_service

    def criar(self, dados, autorizar_usuario):
        payload = validar_pedido(dados)
        autorizar_usuario(payload["usuario_id"])
        resultado = self.pedidos.criar(payload["usuario_id"], payload["itens"])
        self.notifications.pedido_criado(resultado["pedido_id"], payload["usuario_id"])
        return resultado

    def listar_todos(self):
        return self.pedidos.listar_todos()

    def listar_por_usuario(self, usuario_id):
        return self.pedidos.listar_por_usuario(usuario_id)

    def atualizar_status(self, pedido_id, dados):
        status = validar_status(dados)
        self.pedidos.atualizar_status(pedido_id, status)
        self.notifications.status_alterado(pedido_id, status)
