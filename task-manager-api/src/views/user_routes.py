from flask import Blueprint, g, jsonify, request

from src.middlewares.auth import issue_token, optional_auth, require_admin, require_self_or_admin


def build_user_routes(controller):
    bp = Blueprint("users", __name__)

    @bp.get("/users")
    @require_admin
    def get_users():
        return jsonify(controller.list_all()), 200

    @bp.get("/users/<int:user_id>")
    @require_self_or_admin("user_id")
    def get_user(user_id):
        return jsonify(controller.get(user_id)), 200

    @bp.post("/users")
    @optional_auth
    def create_user():
        return jsonify(controller.create(request.get_json(silent=True), g.current_user)), 201

    @bp.put("/users/<int:user_id>")
    @require_self_or_admin("user_id")
    def update_user(user_id):
        return jsonify(controller.update(user_id, request.get_json(silent=True), g.current_user)), 200

    @bp.delete("/users/<int:user_id>")
    @require_admin
    def delete_user(user_id):
        controller.delete(user_id)
        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    @bp.get("/users/<int:user_id>/tasks")
    @require_self_or_admin("user_id")
    def get_user_tasks(user_id):
        return jsonify(controller.tasks(user_id)), 200

    @bp.post("/login")
    def login():
        user = controller.authenticate(request.get_json(silent=True))
        return jsonify({
            "message": "Login realizado com sucesso",
            "user": user.to_dict(),
            "token": issue_token(user.id),
        }), 200

    return bp
