from flask import Blueprint, g, jsonify, request

from src.middlewares.auth import optional_user, require_admin, require_self_or_admin


def build_user_routes(user_controller):
    bp = Blueprint('users', __name__)

    @bp.get('/users')
    @require_admin
    def list_users():
        return jsonify(user_controller.list()), 200

    @bp.get('/users/<int:user_id>')
    @require_self_or_admin('user_id')
    def get_user(user_id):
        return jsonify(user_controller.get(user_id)), 200

    @bp.post('/users')
    def create_user():
        return jsonify(user_controller.create(optional_user(), request.get_json(silent=True))), 201

    @bp.put('/users/<int:user_id>')
    @require_self_or_admin('user_id')
    def update_user(user_id):
        payload = request.get_json(silent=True)
        return jsonify(user_controller.update(g.current_user, user_id, payload)), 200

    @bp.delete('/users/<int:user_id>')
    @require_admin
    def delete_user(user_id):
        return jsonify(user_controller.delete(user_id)), 200

    @bp.get('/users/<int:user_id>/tasks')
    @require_self_or_admin('user_id')
    def get_user_tasks(user_id):
        return jsonify(user_controller.tasks_of(user_id)), 200

    @bp.post('/login')
    def login():
        return jsonify(user_controller.login(request.get_json(silent=True))), 200

    return bp
