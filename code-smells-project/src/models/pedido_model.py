from src.errors import ValidationError

STATUS_INICIAL = "pendente"

_SELECT_PEDIDOS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


class PedidoModel:
    def __init__(self, db):
        self.db = db

    def listar(self, usuario_id=None):
        sql, params = _SELECT_PEDIDOS, ()
        if usuario_id is not None:
            sql += " WHERE p.usuario_id = ?"
            params = (usuario_id,)
        rows = self.db.connection.execute(sql + " ORDER BY p.id, i.id", params).fetchall()

        pedidos = {}
        for row in rows:
            pedido = pedidos.setdefault(row["id"], {
                "id": row["id"],
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            })
            if row["produto_id"] is not None:
                pedido["itens"].append({
                    "produto_id": row["produto_id"],
                    "produto_nome": row["produto_nome"] or "Desconhecido",
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                })
        return list(pedidos.values())

    def criar(self, usuario_id, itens, total):
        """Grava pedido, itens e baixa de estoque numa única transação.

        `itens` traz produto_id, quantidade, preco_unitario e nome já validados.
        """
        conn = self.db.connection
        with conn:
            cur = conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_INICIAL, total),
            )
            pedido_id = cur.lastrowid
            for item in itens:
                conn.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                    (pedido_id, item["produto_id"], item["quantidade"], item["preco_unitario"]),
                )
                baixa = conn.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if baixa.rowcount == 0:
                    # Levanta dentro do `with`: a transação inteira é desfeita.
                    raise ValidationError("Estoque insuficiente para " + item["nome"])
        return pedido_id

    def atualizar_status(self, pedido_id, status):
        conn = self.db.connection
        with conn:
            cur = conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
        return cur.rowcount > 0

    def produto_tem_itens(self, produto_id):
        row = self.db.connection.execute(
            "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
        ).fetchone()
        return row is not None

    def resumo_por_status(self):
        rows = self.db.connection.execute(
            "SELECT status, COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS faturamento "
            "FROM pedidos GROUP BY status"
        ).fetchall()
        return {row["status"]: (row["quantidade"], row["faturamento"]) for row in rows}
