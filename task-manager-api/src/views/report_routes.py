from flask import Blueprint, jsonify

from src.middlewares.error_handler import NotFoundError


def build_report_routes(report_service, user_model):
    bp = Blueprint("reports", __name__)

    @bp.get("/reports/summary")
    def summary_report():
        return jsonify(report_service.summary()), 200

    @bp.get("/reports/user/<int:user_id>")
    def user_report(user_id):
        user = user_model.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return jsonify(report_service.user_report(user)), 200

    return bp
