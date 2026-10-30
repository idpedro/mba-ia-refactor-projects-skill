import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Simulated notification channels; each method only logs for now."""

    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("EMAIL: pedido %s criado para usuario %s", pedido_id, usuario_id)
        logger.info("SMS: seu pedido foi recebido (pedido %s)", pedido_id)
        logger.info("PUSH: novo pedido %s recebido pelo sistema", pedido_id)

    def pedido_aprovado(self, pedido_id):
        logger.info("NOTIFICACAO: pedido %s aprovado, preparar envio", pedido_id)

    def pedido_cancelado(self, pedido_id):
        logger.info("NOTIFICACAO: pedido %s cancelado, devolver estoque", pedido_id)
