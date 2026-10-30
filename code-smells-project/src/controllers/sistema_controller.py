import logging

from src.errors import ForbiddenError, ValidationError

logger = logging.getLogger(__name__)


class SistemaController:
    """Health check, sales report and the (flag-gated) admin tools."""

    def __init__(self, db, settings, produto_model, usuario_model, pedido_model, relatorio_service):
        self.db = db
        self.settings = settings
        self.produtos = produto_model
        self.usuarios = usuario_model
        self.pedidos = pedido_model
        self.relatorios = relatorio_service

    def health(self):
        self.db.connection().execute("SELECT 1")
        return {
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self.produtos.contar(),
                "usuarios": self.usuarios.contar(),
                "pedidos": self.pedidos.contar(),
            },
            "versao": self.settings.APP_VERSION,
            "ambiente": self.settings.APP_ENV,
        }

    def relatorio_vendas(self):
        return self.relatorios.vendas()

    def _exigir_admin(self):
        if not self.settings.ADMIN_ENABLED:
            raise ForbiddenError("Endpoints administrativos desabilitados")

    def reset_database(self):
        self._exigir_admin()
        conn = self.db.connection()
        with conn:
            conn.execute("DELETE FROM itens_pedido")
            conn.execute("DELETE FROM pedidos")
            conn.execute("DELETE FROM produtos")
            conn.execute("DELETE FROM usuarios")
        logger.warning("Banco de dados resetado via /admin/reset-db")

    def executar_query(self, dados):
        """Admin-only raw SQL console; disabled unless ADMIN_ENABLED is set."""
        self._exigir_admin()
        query = dados.get("sql", "") if isinstance(dados, dict) else ""
        if not query:
            raise ValidationError("Query não informada")
        conn = self.db.connection()
        logger.warning("Executando SQL administrativo")
        with conn:
            cur = conn.execute(query)
            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cur.fetchall()]
        return None
