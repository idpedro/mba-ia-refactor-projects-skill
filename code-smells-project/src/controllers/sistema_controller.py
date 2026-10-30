import logging
import sqlite3

from src.controllers.validators import validar_query
from src.errors import ValidationError

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, sistema_model, settings):
        self.sistema = sistema_model
        self.settings = settings

    def health(self):
        return {
            "status": "ok",
            "database": "connected",
            "counts": self.sistema.contagens(),
            "versao": self.settings.APP_VERSION,
            "ambiente": self.settings.AMBIENTE,
        }

    def resetar_banco(self):
        self.sistema.resetar()
        logger.warning("Banco de dados resetado")

    def executar_query(self, dados):
        sql = validar_query(dados)
        try:
            return self.sistema.consulta_somente_leitura(sql)
        except sqlite3.Error as err:
            logger.info("Query administrativa rejeitada: %s", err)
            raise ValidationError("Query inválida")
