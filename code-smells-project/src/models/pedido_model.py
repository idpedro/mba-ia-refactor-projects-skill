from src.errors import ValidationError

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)
PRODUTO_DESCONHECIDO = "Desconhecido"

_SELECT_PEDIDOS_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


def _agrupar_pedidos(rows):
    pedidos = {}
    for r in rows:
        pedido = pedidos.setdefault(r["id"], {
            "id": r["id"], "usuario_id": r["usuario_id"], "status": r["status"],
            "total": r["total"], "criado_em": r["criado_em"], "itens": [],
        })
        if r["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": r["produto_id"],
                "produto_nome": r["produto_nome"] or PRODUTO_DESCONHECIDO,
                "quantidade": r["quantidade"],
                "preco_unitario": r["preco_unitario"],
            })
    return list(pedidos.values())


class PedidoModel:
    def __init__(self, db, produto_model):
        self.db = db
        self.produtos = produto_model

    def listar(self, usuario_id=None):
        sql, params = _SELECT_PEDIDOS_COM_ITENS, []
        if usuario_id is not None:
            sql += " WHERE p.usuario_id = ?"
            params.append(usuario_id)
        sql += " ORDER BY p.id, i.id"
        return _agrupar_pedidos(self.db.connection().execute(sql, params).fetchall())

    def criar(self, usuario_id, itens):
        """Validate every item, then write order, items and stock in one transaction."""
        produtos = self.produtos.buscar_por_ids(item["produto_id"] for item in itens)
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise ValidationError("Produto " + str(item["produto_id"]) + " não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError("Estoque insuficiente para " + produto["nome"])
        total = sum(produtos[item["produto_id"]]["preco"] * item["quantidade"] for item in itens)

        conn = self.db.connection()
        with conn:  # commits on success, rolls back on any exception
            cur = conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_PENDENTE, total),
            )
            pedido_id = cur.lastrowid
            for item in itens:
                produto = produtos[item["produto_id"]]
                conn.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                    (pedido_id, item["produto_id"], item["quantidade"], produto["preco"]),
                )
                atualizado = conn.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if atualizado.rowcount == 0:
                    raise ValidationError("Estoque insuficiente para " + produto["nome"])
        return {"pedido_id": pedido_id, "total": total}

    def atualizar_status(self, pedido_id, novo_status):
        conn = self.db.connection()
        with conn:
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))

    def totais_por_status(self):
        """One aggregate query: {status: (quantidade, soma_total)}."""
        rows = self.db.connection().execute(
            "SELECT status, COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS soma FROM pedidos GROUP BY status"
        ).fetchall()
        return {row["status"]: (row["quantidade"], row["soma"]) for row in rows}

    def contar(self):
        return self.db.connection().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
