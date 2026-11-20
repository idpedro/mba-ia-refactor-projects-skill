"""Tratamento central de erros: formato {"erro": ...} preservado, detalhes só no log."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        if err.status >= 500:
            logger.error("Erro de aplicação: %s", err.message, exc_info=err)
        return jsonify({"erro": err.message, "sucesso": False}), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        # 404/405 e afins mantêm a resposta nativa do Flask, como no código original.
        return err

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro não tratado: %s", err)
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
