import logging

from src.controllers.validators import validar_consulta

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, sistema_model, relatorio_service, settings):
        self.sistema = sistema_model
        self.relatorios = relatorio_service
        self.settings = settings

    def health(self):
        return {
            "status": "ok",
            "database": "connected",
            "counts": self.sistema.contagens(),
            "versao": self.settings["APP_VERSION"],
            "ambiente": self.settings["ENVIRONMENT"],
        }

    def relatorio_vendas(self):
        return self.relatorios.vendas()

    def resetar_banco(self):
        self.sistema.resetar()
        logger.warning("Banco de dados resetado")

    def executar_consulta(self, dados):
        return self.sistema.consultar(validar_consulta(dados))
