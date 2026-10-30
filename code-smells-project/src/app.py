import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.sistema_controller import SistemaController
from src.controllers.usuario_controller import UsuarioController
from src.database import Database
from src.middlewares.error_handler import register_error_handlers
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.usuario_model import UsuarioModel
from src.services.notification_service import NotificationService
from src.services.relatorio_service import RelatorioService
from src.views.pedido_routes import build_pedido_routes
from src.views.produto_routes import build_produto_routes
from src.views.sistema_routes import build_sistema_routes
from src.views.usuario_routes import build_usuario_routes


def create_app(settings=Settings):
    """Composition root: config, database, models, services, controllers, routes."""
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)

    db = Database(settings.DATABASE_PATH)
    db.init_app(app)

    produtos = ProdutoModel(db)
    usuarios = UsuarioModel(db)
    pedidos = PedidoModel(db, produtos)
    relatorios = RelatorioService(pedidos)
    notifications = NotificationService()

    app.register_blueprint(build_produto_routes(ProdutoController(produtos)))
    app.register_blueprint(build_usuario_routes(UsuarioController(usuarios)))
    app.register_blueprint(build_pedido_routes(PedidoController(pedidos, notifications)))
    app.register_blueprint(build_sistema_routes(
        SistemaController(db, settings, produtos, usuarios, pedidos, relatorios),
        settings.APP_VERSION,
    ))
    register_error_handlers(app)
    return app
