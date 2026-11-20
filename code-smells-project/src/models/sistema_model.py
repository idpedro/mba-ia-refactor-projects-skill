"""Consultas administrativas e de saúde do sistema."""
import sqlite3

from src.errors import DatabaseUnavailableError

# Allow-list de consultas administrativas: SQL fixo, somente leitura, sem colunas de credencial.
CONSULTAS_ADMIN = {
    "produtos_sem_estoque": "SELECT id, nome, categoria FROM produtos WHERE ativo = 1 AND estoque = 0 ORDER BY id",
    "pedidos_por_status": "SELECT status, COUNT(*) AS total FROM pedidos GROUP BY status ORDER BY status",
    "vendas_por_produto": (
        "SELECT pr.id, pr.nome, SUM(i.quantidade) AS quantidade, "
        "ROUND(SUM(i.quantidade * i.preco_unitario), 2) AS receita "
        "FROM itens_pedido i JOIN produtos pr ON pr.id = i.produto_id "
        "GROUP BY pr.id, pr.nome ORDER BY receita DESC"
    ),
}


class SistemaModel:
    def __init__(self, db):
        self.db = db

    def contagens(self):
        try:
            row = self.db.query_one(
                "SELECT (SELECT COUNT(*) FROM produtos) AS produtos, "
                "(SELECT COUNT(*) FROM usuarios) AS usuarios, "
                "(SELECT COUNT(*) FROM pedidos) AS pedidos"
            )
        except sqlite3.Error as exc:
            raise DatabaseUnavailableError("Banco de dados indisponível") from exc
        return {"produtos": row["produtos"], "usuarios": row["usuarios"], "pedidos": row["pedidos"]}

    @staticmethod
    def consulta_permitida(nome):
        return nome in CONSULTAS_ADMIN

    def executar_consulta(self, nome):
        return [dict(row) for row in self.db.query(CONSULTAS_ADMIN[nome])]

    def resetar(self):
        with self.db.transaction() as conexao:
            conexao.execute("DELETE FROM itens_pedido")
            conexao.execute("DELETE FROM pedidos")
            conexao.execute("DELETE FROM produtos")
            conexao.execute("DELETE FROM usuarios")
