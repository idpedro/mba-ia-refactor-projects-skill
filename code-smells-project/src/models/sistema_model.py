class SistemaModel:
    def __init__(self, db):
        self.db = db

    def contagens(self):
        row = self.db.connection.execute(
            "SELECT (SELECT COUNT(*) FROM produtos) AS produtos, "
            "(SELECT COUNT(*) FROM usuarios) AS usuarios, "
            "(SELECT COUNT(*) FROM pedidos) AS pedidos"
        ).fetchone()
        return {"produtos": row["produtos"], "usuarios": row["usuarios"], "pedidos": row["pedidos"]}

    def resetar(self):
        conn = self.db.connection
        with conn:
            # Filhos antes dos pais, tudo na mesma transação.
            conn.execute("DELETE FROM itens_pedido")
            conn.execute("DELETE FROM pedidos")
            conn.execute("DELETE FROM produtos")
            conn.execute("DELETE FROM usuarios")

    def consulta_somente_leitura(self, sql):
        conn = self.db.readonly_connection()
        try:
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.close()
