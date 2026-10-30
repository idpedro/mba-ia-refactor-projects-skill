CAMPOS_PRODUTO = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def produto_to_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PRODUTO}


class ProdutoModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        rows = self.db.connection().execute("SELECT * FROM produtos").fetchall()
        return [produto_to_dict(row) for row in rows]

    def buscar_por_id(self, produto_id):
        row = self.db.connection().execute(
            "SELECT * FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        return produto_to_dict(row) if row else None

    def buscar_por_ids(self, produto_ids):
        ids = list(set(produto_ids))
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self.db.connection().execute(
            f"SELECT * FROM produtos WHERE id IN ({placeholders})", ids
        ).fetchall()
        return {row["id"]: produto_to_dict(row) for row in rows}

    def buscar(self, termo, categoria=None, preco_min=None, preco_max=None):
        clauses, params = ["1=1"], []
        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max:
            clauses.append("preco <= ?")
            params.append(preco_max)
        rows = self.db.connection().execute(
            f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params
        ).fetchall()
        return [produto_to_dict(row) for row in rows]

    def criar(self, nome, descricao, preco, estoque, categoria):
        conn = self.db.connection()
        with conn:
            cur = conn.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
        return cur.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        conn = self.db.connection()
        with conn:
            conn.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )

    def deletar(self, produto_id):
        # Order history keeps its itens_pedido rows on purpose; reads label a
        # missing product as "Desconhecido".
        conn = self.db.connection()
        with conn:
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def contar(self):
        return self.db.connection().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
