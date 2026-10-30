from flask import Blueprint, g, jsonify, request

from src.middlewares.auth import require_admin, require_auth, require_self_or_admin


def build_pedido_routes(pedido_controller, relatorio_service):
    bp = Blueprint("pedidos", __name__)

    @bp.post("/pedidos")
    @require_auth
    def criar_pedido():
        resultado = pedido_controller.criar(request.get_json(silent=True), g.current_user)
        return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201

    @bp.get("/pedidos")
    @require_admin
    def listar_todos_pedidos():
        return jsonify({"dados": pedido_controller.listar(), "sucesso": True}), 200

    @bp.get("/pedidos/usuario/<int:usuario_id>")
    @require_self_or_admin("usuario_id")
    def listar_pedidos_usuario(usuario_id):
        return jsonify({"dados": pedido_controller.listar_do_usuario(usuario_id), "sucesso": True}), 200

    @bp.put("/pedidos/<int:pedido_id>/status")
    @require_admin
    def atualizar_status_pedido(pedido_id):
        pedido_controller.atualizar_status(pedido_id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    @bp.get("/relatorios/vendas")
    @require_admin
    def relatorio_vendas():
        return jsonify({"dados": relatorio_service.vendas(), "sucesso": True}), 200

    return bp
