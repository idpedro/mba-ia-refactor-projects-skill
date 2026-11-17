from src.errors import ValidationError

STATUS_PEDIDO = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
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

    def criar(self, usuario_id, itens):
        """Valida preço e estoque e grava pedido, itens e baixa de estoque numa única transação."""
        conn = self.db.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            precos, total = {}, 0
            for item in itens:
                produto = conn.execute(
                    "SELECT nome, preco, estoque FROM produtos WHERE id = ?", (item["produto_id"],)
                ).fetchone()
                if produto is None:
                    raise ValidationError(f"Produto {item['produto_id']} não encontrado")
                if produto["estoque"] < item["quantidade"]:
                    raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
                precos[item["produto_id"]] = produto["preco"]
                total += produto["preco"] * item["quantidade"]

            pedido_id = conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_INICIAL, total),
            ).lastrowid
            for item in itens:
                conn.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                    (pedido_id, item["produto_id"], item["quantidade"], precos[item["produto_id"]]),
                )
                baixa = conn.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if baixa.rowcount == 0:
                    raise ValidationError("Estoque insuficiente para o produto " + str(item["produto_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return {"pedido_id": pedido_id, "total": total}

    def listar_todos(self):
        rows = self.db.connection().execute(_SELECT_PEDIDOS + " ORDER BY p.id, i.id").fetchall()
        return self._agrupar(rows)

    def listar_por_usuario(self, usuario_id):
        rows = self.db.connection().execute(
            _SELECT_PEDIDOS + " WHERE p.usuario_id = ? ORDER BY p.id, i.id", (usuario_id,)
        ).fetchall()
        return self._agrupar(rows)

    @staticmethod
    def _agrupar(rows):
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

    def atualizar_status(self, pedido_id, novo_status):
        conn = self.db.connection()
        with conn:
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
