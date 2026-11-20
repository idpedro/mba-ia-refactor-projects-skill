"""Composition root: monta configuração, banco, serviços, controllers e rotas."""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.controllers.category_controller import CategoryController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.database import init_database
from src.middlewares.error_handler import register_error_handlers
from src.services.auth_service import AuthService
from src.services.credential_service import migrate_credentials
from src.services.notification_service import NotificationService
from src.services.report_service import ReportService
from src.views.category_routes import build_category_routes
from src.views.report_routes import build_report_routes
from src.views.system_routes import build_system_routes
from src.views.task_routes import build_task_routes
from src.views.user_routes import build_user_routes


def create_app(settings=Settings):
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    app = Flask(__name__)
    app.config.from_object(settings)
    if settings.CORS_ORIGINS:
        CORS(app, origins=settings.CORS_ORIGINS)

    init_database(app)
    with app.app_context():
        migrate_credentials(settings)

    auth_service = AuthService(settings.SECRET_KEY, settings.TOKEN_MAX_AGE)
    app.extensions['auth_service'] = auth_service
    notifications = NotificationService(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.SMTP_TIMEOUT,
    )
    report_service = ReportService()

    app.register_blueprint(build_system_routes())
    app.register_blueprint(build_task_routes(TaskController(notifications), report_service))
    app.register_blueprint(build_user_routes(UserController(auth_service)))
    app.register_blueprint(build_report_routes(report_service))
    app.register_blueprint(build_category_routes(CategoryController()))
    register_error_handlers(app)
    return app
