from flask import Blueprint, jsonify, request

ENDPOINTS_PUBLICOS = {
    "produtos": "/produtos",
    "usuarios": "/usuarios",
    "pedidos": "/pedidos",
    "login": "/login",
    "relatorios": "/relatorios/vendas",
    "health": "/health",
}


def build_sistema_routes(controller, versao):
    bp = Blueprint("sistema", __name__)

    @bp.get("/")
    def index():
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": versao,
            "endpoints": ENDPOINTS_PUBLICOS,
        })

    @bp.get("/health")
    def health_check():
        return jsonify(controller.health()), 200

    @bp.get("/relatorios/vendas")
    def relatorio_vendas():
        return jsonify({"dados": controller.relatorio_vendas(), "sucesso": True}), 200

    @bp.post("/admin/reset-db")
    def reset_database():
        controller.reset_database()
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200

    @bp.post("/admin/query")
    def executar_query():
        dados = controller.executar_query(request.get_json(silent=True))
        if dados is None:
            return jsonify({"mensagem": "Query executada", "sucesso": True}), 200
        return jsonify({"dados": dados, "sucesso": True}), 200

    return bp
