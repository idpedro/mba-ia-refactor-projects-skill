"""Composition root: config, banco, serviços, controllers, rotas e tratamento de erros."""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.controllers.category_controller import CategoryController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.database import init_db
from src.middlewares.error_handler import register_error_handlers
from src.services.notification_service import NotificationService
from src.services.report_service import ReportService
from src.views.category_routes import build_category_routes
from src.views.index_routes import build_index_routes
from src.views.report_routes import build_report_routes
from src.views.task_routes import build_task_routes
from src.views.user_routes import build_user_routes


def create_app(settings=Settings):
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)
    init_db(app)

    notifications = NotificationService(
        settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASSWORD
    )
    reports = ReportService()
    users = UserController()

    app.register_blueprint(build_index_routes())
    app.register_blueprint(build_task_routes(TaskController(notifications, reports)))
    app.register_blueprint(build_user_routes(users))
    app.register_blueprint(build_report_routes(reports, users))
    app.register_blueprint(build_category_routes(CategoryController()))
    register_error_handlers(app)
    return app
