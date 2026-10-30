from flask import Blueprint, g, jsonify, request

from src.middlewares.auth import require_auth


def build_task_routes(controller):
    bp = Blueprint("tasks", __name__)

    @bp.get("/tasks")
    @require_auth
    def get_tasks():
        return jsonify(controller.list_all()), 200

    @bp.get("/tasks/<int:task_id>")
    @require_auth
    def get_task(task_id):
        return jsonify(controller.get(task_id)), 200

    @bp.post("/tasks")
    @require_auth
    def create_task():
        return jsonify(controller.create(request.get_json(silent=True), g.current_user)), 201

    @bp.put("/tasks/<int:task_id>")
    @require_auth
    def update_task(task_id):
        return jsonify(controller.update(task_id, request.get_json(silent=True), g.current_user)), 200

    @bp.delete("/tasks/<int:task_id>")
    @require_auth
    def delete_task(task_id):
        controller.delete(task_id, g.current_user)
        return jsonify({"message": "Task deletada com sucesso"}), 200

    @bp.get("/tasks/search")
    @require_auth
    def search_tasks():
        return jsonify(controller.search(request.args)), 200

    @bp.get("/tasks/stats")
    @require_auth
    def task_stats():
        return jsonify(controller.stats()), 200

    return bp
