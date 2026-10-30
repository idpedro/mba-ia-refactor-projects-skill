from src.controllers.validators import validar_pedido, validar_status
from src.errors import ForbiddenError, NotFoundError, ValidationError
from src.models.usuario_model import TIPO_ADMIN


class PedidoController:
    def __init__(self, pedido_model, produto_model, notification_service):
        self.pedidos = pedido_model
        self.produtos = produto_model
        self.notifications = notification_service

    def criar(self, dados, usuario_atual):
        payload = validar_pedido(dados)
        usuario_id = payload["usuario_id"]
        if usuario_atual["id"] != usuario_id and usuario_atual["tipo"] != TIPO_ADMIN:
            raise ForbiddenError("Acesso negado")

        itens = []
        for item in payload["itens"]:
            produto = self.produtos.buscar_por_id(item["produto_id"])
            if produto is None:
                raise ValidationError("Produto " + str(item["produto_id"]) + " não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError("Estoque insuficiente para " + produto["nome"])
            itens.append({**item, "preco_unitario": produto["preco"], "nome": produto["nome"]})

        total = sum(item["preco_unitario"] * item["quantidade"] for item in itens)
        pedido_id = self.pedidos.criar(usuario_id, itens, total)
        self.notifications.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar(self):
        return self.pedidos.listar()

    def listar_do_usuario(self, usuario_id):
        return self.pedidos.listar(usuario_id=usuario_id)

    def atualizar_status(self, pedido_id, dados):
        status = validar_status(dados)
        if not self.pedidos.atualizar_status(pedido_id, status):
            raise NotFoundError("Pedido não encontrado")
        self.notifications.status_alterado(pedido_id, status)
