"""Composition root: config, banco, serviços, controllers, rotas e tratamento de erros."""
import logging

from flask import Flask
from flask_cors import CORS

from src.config import Settings
from src.controllers.category_controller import CategoryController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.database import db, init_db
from src.middlewares.auth import build_auth_guards
from src.middlewares.error_handler import register_error_handlers
from src.models import Category, Task, User
from src.services.auth_service import AuthService
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

    notifications = NotificationService.from_settings(settings)
    auth = AuthService(settings.SECRET_KEY, settings.AUTH_TOKEN_MAX_AGE)
    reports = ReportService(Task, User, Category)

    task_controller = TaskController(Task, User, Category, reports, notifications)
    user_controller = UserController(User, Task, auth)
    category_controller = CategoryController(Category, Task)
    require_auth, require_self_or_admin = build_auth_guards(user_controller)

    app.register_blueprint(build_index_routes())
    app.register_blueprint(build_task_routes(task_controller, require_auth))
    app.register_blueprint(build_user_routes(user_controller, require_self_or_admin))
    app.register_blueprint(build_report_routes(reports, User))
    app.register_blueprint(build_category_routes(category_controller, require_auth))
    register_error_handlers(app, db)
    return app
