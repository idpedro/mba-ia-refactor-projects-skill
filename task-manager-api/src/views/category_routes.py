from flask import Blueprint, jsonify, request

from src.middlewares.auth import require_admin, require_auth


def build_category_routes(category_controller):
    bp = Blueprint('categories', __name__)

    @bp.get('/categories')
    @require_auth
    def list_categories():
        return jsonify(category_controller.list()), 200

    @bp.post('/categories')
    @require_admin
    def create_category():
        return jsonify(category_controller.create(request.get_json(silent=True))), 201

    @bp.put('/categories/<int:cat_id>')
    @require_admin
    def update_category(cat_id):
        return jsonify(category_controller.update(cat_id, request.get_json(silent=True))), 200

    @bp.delete('/categories/<int:cat_id>')
    @require_admin
    def delete_category(cat_id):
        return jsonify(category_controller.delete(cat_id)), 200

    return bp
