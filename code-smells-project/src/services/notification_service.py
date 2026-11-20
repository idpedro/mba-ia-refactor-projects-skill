"""Notificações de pedido. Os canais ainda são simulados: cada envio vira uma linha de log."""
import logging

from src.models.constants import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


class NotificationService:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
        logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
        logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")

    def status_alterado(self, pedido_id, status):
        if status == STATUS_APROVADO:
            logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
        elif status == STATUS_CANCELADO:
            logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)
