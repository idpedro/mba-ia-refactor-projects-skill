"""Persistência de pedidos: criação atômica com baixa de estoque e leitura sem N+1."""
from src.errors import ValidationError
from src.models.constants import STATUS_PENDENTE

SELECT_PEDIDOS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


def _montar_pedidos(rows):
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


class PedidoModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        return _montar_pedidos(self.db.query(SELECT_PEDIDOS + " ORDER BY p.id, i.id"))

    def listar_por_usuario(self, usuario_id):
        rows = self.db.query(SELECT_PEDIDOS + " WHERE p.usuario_id = ? ORDER BY p.id, i.id", (usuario_id,))
        return _montar_pedidos(rows)

    def criar(self, usuario_id, quantidades):
        """quantidades: {produto_id: quantidade total}. Tudo ou nada, numa transação serializada."""
        ids = list(quantidades)
        marcadores = ",".join("?" for _ in ids)
        with self.db.transaction() as conexao:
            rows = conexao.execute(
                f"SELECT id, nome, preco, estoque FROM produtos WHERE ativo = 1 AND id IN ({marcadores})", ids
            ).fetchall()
            produtos = {row["id"]: row for row in rows}
            for produto_id, quantidade in quantidades.items():
                produto = produtos.get(produto_id)
                if produto is None:
                    raise ValidationError(f"Produto {produto_id} não encontrado")
                if produto["estoque"] < quantidade:
                    raise ValidationError(f"Estoque insuficiente para {produto['nome']}")

            total = sum(produtos[produto_id]["preco"] * quantidade for produto_id, quantidade in quantidades.items())
            pedido_id = conexao.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_PENDENTE, total),
            ).lastrowid
            for produto_id, quantidade in quantidades.items():
                conexao.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                    (pedido_id, produto_id, quantidade, produtos[produto_id]["preco"]),
                )
                baixa = conexao.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (quantidade, produto_id, quantidade),
                )
                if baixa.rowcount != 1:
                    raise ValidationError(f"Estoque insuficiente para {produtos[produto_id]['nome']}")
        return {"pedido_id": pedido_id, "total": total}

    def atualizar_status(self, pedido_id, status):
        """Devolve True se o pedido existe."""
        cursor = self.db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
        return cursor.rowcount == 1

    def totais(self):
        row = self.db.query_one("SELECT COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS soma FROM pedidos")
        return row["quantidade"], row["soma"]

    def contagem_por_status(self):
        rows = self.db.query("SELECT status, COUNT(*) AS quantidade FROM pedidos GROUP BY status")
        return {row["status"]: row["quantidade"] for row in rows}
