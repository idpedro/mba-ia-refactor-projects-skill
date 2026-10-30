import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Notificações simuladas: hoje só registram no log; o ponto de integração com email/SMS/push é aqui."""

    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("EMAIL: pedido %s criado para usuario %s", pedido_id, usuario_id)
        logger.info("SMS: pedido %s recebido", pedido_id)
        logger.info("PUSH: novo pedido %s recebido pelo sistema", pedido_id)

    def status_alterado(self, pedido_id, status):
        if status == "aprovado":
            logger.info("Pedido %s aprovado: preparar envio", pedido_id)
        elif status == "cancelado":
            logger.info("Pedido %s cancelado: devolver estoque", pedido_id)
