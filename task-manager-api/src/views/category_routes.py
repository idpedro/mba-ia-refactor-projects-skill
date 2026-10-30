from flask import Blueprint, jsonify, request

from src.middlewares.auth import require_admin, require_auth


def build_category_routes(controller):
    bp = Blueprint("categories", __name__)

    @bp.get("/categories")
    @require_auth
    def get_categories():
        return jsonify(controller.list_all()), 200

    @bp.post("/categories")
    @require_admin
    def create_category():
        return jsonify(controller.create(request.get_json(silent=True))), 201

    @bp.put("/categories/<int:cat_id>")
    @require_admin
    def update_category(cat_id):
        return jsonify(controller.update(cat_id, request.get_json(silent=True))), 200

    @bp.delete("/categories/<int:cat_id>")
    @require_admin
    def delete_category(cat_id):
        controller.delete(cat_id)
        return jsonify({"message": "Categoria deletada"}), 200

    return bp
