from flask import Blueprint, jsonify, request


def build_task_routes(controller, require_auth):
    bp = Blueprint("tasks", __name__)

    @bp.get("/tasks")
    def list_tasks():
        return jsonify(controller.list_tasks()), 200

    @bp.get("/tasks/<int:task_id>")
    def get_task(task_id):
        return jsonify(controller.get_task(task_id)), 200

    @bp.post("/tasks")
    @require_auth
    def create_task():
        return jsonify(controller.create_task(request.get_json())), 201

    @bp.put("/tasks/<int:task_id>")
    @require_auth
    def update_task(task_id):
        return jsonify(controller.update_task(task_id, request.get_json())), 200

    @bp.delete("/tasks/<int:task_id>")
    @require_auth
    def delete_task(task_id):
        controller.delete_task(task_id)
        return jsonify({"message": "Task deletada com sucesso"}), 200

    @bp.get("/tasks/search")
    def search_tasks():
        return jsonify(controller.search(request.args)), 200

    @bp.get("/tasks/stats")
    def task_stats():
        return jsonify(controller.stats()), 200

    return bp
