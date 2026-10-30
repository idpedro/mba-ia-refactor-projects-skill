import logging
import sqlite3

from flask import Blueprint, jsonify, request

from src.middlewares.auth import require_admin

logger = logging.getLogger(__name__)


def build_sistema_routes(controller):
    bp = Blueprint("sistema", __name__)

    @bp.get("/")
    def index():
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": controller.settings.APP_VERSION,
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
        try:
            return jsonify(controller.health()), 200
        except sqlite3.Error:
            logger.exception("Health check falhou")
            return jsonify({"status": "erro", "detalhes": "Banco de dados indisponível"}), 500

    @bp.post("/admin/reset-db")
    @require_admin
    def reset_database():
        controller.resetar_banco()
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200

    @bp.post("/admin/query")
    @require_admin
    def executar_query():
        dados = controller.executar_query(request.get_json(silent=True))
        return jsonify({"dados": dados, "sucesso": True}), 200

    return bp
