"""Erros de domínio e tratamento centralizado: toda resposta de erro é `{"error": "..."}`."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

INTERNAL_ERROR_MESSAGE = "Erro interno"


class AppError(Exception):
    status = 500

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status = 400


class UnauthorizedError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


class NotFoundError(AppError):
    status = 404


class ConflictError(AppError):
    status = 409


def register_error_handlers(app, db):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        db.session.rollback()
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify({"error": err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        logger.exception("Erro não tratado")
        return jsonify({"error": INTERNAL_ERROR_MESSAGE}), 500
