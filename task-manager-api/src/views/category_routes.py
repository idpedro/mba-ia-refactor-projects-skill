from flask import Blueprint, jsonify, request


def build_category_routes(controller, require_auth):
    bp = Blueprint("categories", __name__)

    @bp.get("/categories")
    def list_categories():
        return jsonify(controller.list_categories()), 200

    @bp.post("/categories")
    @require_auth
    def create_category():
        return jsonify(controller.create_category(request.get_json())), 201

    @bp.put("/categories/<int:cat_id>")
    @require_auth
    def update_category(cat_id):
        return jsonify(controller.update_category(cat_id, request.get_json())), 200

    @bp.delete("/categories/<int:cat_id>")
    @require_auth
    def delete_category(cat_id):
        controller.delete_category(cat_id)
        return jsonify({"message": "Categoria deletada"}), 200

    return bp
