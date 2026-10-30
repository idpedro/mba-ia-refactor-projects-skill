CAMPOS_PRODUTO = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def _to_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PRODUTO}


class ProdutoModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        rows = self.db.connection.execute("SELECT * FROM produtos").fetchall()
        return [_to_dict(row) for row in rows]

    def buscar_por_id(self, produto_id):
        row = self.db.connection.execute(
            "SELECT * FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        return _to_dict(row) if row else None

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        clauses, params = ["1=1"], []
        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clauses.append("preco <= ?")
            params.append(preco_max)
        # O f-string só junta cláusulas fixas; todos os valores vão por `params`.
        rows = self.db.connection.execute(
            f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params
        ).fetchall()
        return [_to_dict(row) for row in rows]

    def criar(self, nome, descricao, preco, estoque, categoria):
        conn = self.db.connection
        with conn:
            cur = conn.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
        return cur.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        conn = self.db.connection
        with conn:
            conn.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )

    def deletar(self, produto_id):
        conn = self.db.connection
        with conn:
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
