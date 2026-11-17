from datetime import datetime

from flask import Blueprint, jsonify


def build_index_routes():
    bp = Blueprint('index', __name__)

    @bp.get('/health')
    def health():
        return jsonify({'status': 'ok', 'timestamp': str(datetime.now())})

    @bp.get('/')
    def index():
        return jsonify({'message': 'Task Manager API', 'version': '1.0'})

    return bp
