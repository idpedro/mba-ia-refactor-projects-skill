from flask import Blueprint, jsonify

from src.middlewares.auth import require_admin, require_self_or_admin


def build_report_routes(controller):
    bp = Blueprint('reports', __name__)

    @bp.get('/reports/summary')
    @require_admin
    def summary_report():
        return jsonify(controller.summary()), 200

    @bp.get('/reports/user/<int:user_id>')
    @require_self_or_admin('user_id')
    def user_report(user_id):
        return jsonify(controller.user_report(user_id)), 200

    return bp
