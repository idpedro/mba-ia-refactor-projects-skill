import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings, configure_logging
from src.controllers.category_controller import CategoryController
from src.controllers.report_controller import ReportController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.database import init_db
from src.middlewares.error_handler import register_error_handlers
from src.models import Category, Task, User
from src.services.report_service import ReportService
from src.views.category_routes import build_category_routes
from src.views.index_routes import build_index_routes
from src.views.report_routes import build_report_routes
from src.views.task_routes import build_task_routes
from src.views.user_routes import build_user_routes

logger = logging.getLogger(__name__)


def create_app(settings=Settings):
    configure_logging(settings.LOG_LEVEL)
    if not settings.SECRET_KEY_FROM_ENV:
        logger.warning('SECRET_KEY não definido: usando chave aleatória; tokens expiram a cada reinício')

    app = Flask(__name__, instance_path=settings.INSTANCE_PATH)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)
    init_db(app)
    app.extensions['user_model'] = User

    reports = ReportService(Task, User, Category)
    app.register_blueprint(build_index_routes())
    app.register_blueprint(build_task_routes(TaskController(Task, User, Category, reports)))
    app.register_blueprint(build_user_routes(UserController(User, Task)))
    app.register_blueprint(build_category_routes(CategoryController(Category)))
    app.register_blueprint(build_report_routes(ReportController(User, reports)))
    register_error_handlers(app)
    return app
