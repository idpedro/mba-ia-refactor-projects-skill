from flask import Blueprint, jsonify, request

from src.middlewares.auth import require_admin


def build_sistema_routes(controller):
    bp = Blueprint("sistema", __name__)

    @bp.get("/")
    def index():
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": "1.0.0",
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    @bp.get("/health")
    def health_check():
        return jsonify(controller.health()), 200

    @bp.get("/relatorios/vendas")
    @require_admin
    def relatorio_vendas():
        return jsonify({"dados": controller.relatorio_vendas(), "sucesso": True}), 200

    @bp.post("/admin/reset-db")
    @require_admin
    def reset_database():
        controller.resetar_banco()
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200

    @bp.post("/admin/query")
    @require_admin
    def executar_query():
        dados = controller.executar_consulta(request.get_json(silent=True))
        return jsonify({"dados": dados, "sucesso": True}), 200

    return bp
