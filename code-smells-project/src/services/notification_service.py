import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Efeitos colaterais simulados (e-mail, SMS, push): só registram em log, sem guardar estado."""

    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("E-mail: pedido %s criado para o usuário %s", pedido_id, usuario_id)
        logger.info("SMS: pedido %s recebido", pedido_id)
        logger.info("Push: novo pedido %s recebido pelo sistema", pedido_id)

    def status_alterado(self, pedido_id, status):
        if status == "aprovado":
            logger.info("Pedido %s aprovado: preparar envio", pedido_id)
        elif status == "cancelado":
            logger.info("Pedido %s cancelado: devolver estoque", pedido_id)
