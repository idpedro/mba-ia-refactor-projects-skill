import logging

from src.errors import ValidationError

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, sistema_model, versao):
        self.sistema = sistema_model
        self.versao = versao

    def health(self):
        return {"status": "ok", "database": "connected", "counts": self.sistema.contagens(), "versao": self.versao}

    def resetar_banco(self, ator):
        self.sistema.resetar()
        logger.warning("Banco de dados resetado pelo usuário id=%s", ator["id"])

    def consultar(self, dados):
        nome = dados.get("consulta") if isinstance(dados, dict) else None
        if not isinstance(nome, str) or not self.sistema.consulta_permitida(nome):
            raise ValidationError("Consulta não permitida")
        return self.sistema.executar_consulta(nome)
