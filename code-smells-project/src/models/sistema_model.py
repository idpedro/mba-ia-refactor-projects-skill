import re

from src.errors import ValidationError

_SELECT_UNICO = re.compile(r"^\s*select\b", re.IGNORECASE)


class SistemaModel:
    def __init__(self, db):
        self.db = db

    def contagens(self):
        conn = self.db.connection()
        return {
            "produtos": conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0],
            "usuarios": conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0],
            "pedidos": conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0],
        }

    def resumo_pedidos(self):
        rows = self.db.connection().execute(
            "SELECT status, COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS faturamento "
            "FROM pedidos GROUP BY status"
        ).fetchall()
        return {row["status"]: (row["quantidade"], row["faturamento"]) for row in rows}

    def resetar(self):
        conn = self.db.connection()
        with conn:
            conn.execute("DELETE FROM itens_pedido")
            conn.execute("DELETE FROM pedidos")
            conn.execute("DELETE FROM produtos")
            conn.execute("DELETE FROM usuarios")

    def consultar(self, sql):
        """Executa uma única instrução SELECT numa conexão somente leitura."""
        instrucao = sql.strip().rstrip(";").strip()
        if not _SELECT_UNICO.match(instrucao) or ";" in instrucao:
            raise ValidationError("Apenas uma consulta SELECT é permitida")
        conn = self.db.connect(read_only=True)
        try:
            return [dict(row) for row in conn.execute(instrucao).fetchall()]
        except Exception:
            raise ValidationError("Consulta inválida")
        finally:
            conn.close()
