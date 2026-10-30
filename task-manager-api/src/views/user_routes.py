from flask import Blueprint, jsonify, request


def build_user_routes(controller, require_self_or_admin):
    bp = Blueprint("users", __name__)

    @bp.get("/users")
    def list_users():
        return jsonify(controller.list_users()), 200

    @bp.get("/users/<int:user_id>")
    def get_user(user_id):
        return jsonify(controller.get_user(user_id)), 200

    @bp.post("/users")
    def create_user():
        return jsonify(controller.create_user(request.get_json())), 201

    @bp.put("/users/<int:user_id>")
    @require_self_or_admin
    def update_user(user_id):
        return jsonify(controller.update_user(user_id, request.get_json())), 200

    @bp.delete("/users/<int:user_id>")
    @require_self_or_admin
    def delete_user(user_id):
        controller.delete_user(user_id)
        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    @bp.get("/users/<int:user_id>/tasks")
    def list_user_tasks(user_id):
        return jsonify(controller.list_user_tasks(user_id)), 200

    @bp.post("/login")
    def login():
        return jsonify(controller.login(request.get_json())), 200

    return bp
