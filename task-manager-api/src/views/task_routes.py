from flask import Blueprint, g, jsonify, request

from src.controllers.task_controller import visible_owner
from src.middlewares.auth import require_auth


def build_task_routes(task_controller, report_service):
    bp = Blueprint('tasks', __name__)

    @bp.get('/tasks')
    @require_auth
    def list_tasks():
        return jsonify(task_controller.list(g.current_user)), 200

    @bp.get('/tasks/<int:task_id>')
    @require_auth
    def get_task(task_id):
        return jsonify(task_controller.get(g.current_user, task_id)), 200

    @bp.post('/tasks')
    @require_auth
    def create_task():
        return jsonify(task_controller.create(g.current_user, request.get_json(silent=True))), 201

    @bp.put('/tasks/<int:task_id>')
    @require_auth
    def update_task(task_id):
        payload = request.get_json(silent=True)
        return jsonify(task_controller.update(g.current_user, task_id, payload)), 200

    @bp.delete('/tasks/<int:task_id>')
    @require_auth
    def delete_task(task_id):
        return jsonify(task_controller.delete(g.current_user, task_id)), 200

    @bp.get('/tasks/search')
    @require_auth
    def search_tasks():
        return jsonify(task_controller.search(g.current_user, request.args)), 200

    @bp.get('/tasks/stats')
    @require_auth
    def task_stats():
        return jsonify(report_service.task_stats(owner_id=visible_owner(g.current_user))), 200

    return bp
