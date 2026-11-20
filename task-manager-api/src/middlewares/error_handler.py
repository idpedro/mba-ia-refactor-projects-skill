"""Tratamento central de erros: toda resposta de erro é JSON `{"error": ...}`."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.errors import AppError

logger = logging.getLogger(__name__)

INTERNAL_ERROR_MESSAGE = 'Erro interno'
HTTP_MESSAGES = {
    400: 'Dados inválidos',
    404: 'Recurso não encontrado',
    405: 'Método não permitido',
    415: 'Dados inválidos',
}


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify({'error': error.message}), error.status

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({'error': HTTP_MESSAGES.get(error.code, error.name)}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        logger.exception('Erro não tratado')
        return jsonify({'error': INTERNAL_ERROR_MESSAGE}), 500
