"""Persistência de produtos. Produto excluído fica inativo (ativo = 0) para preservar o histórico."""

COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def _produto_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


class ProdutoModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        rows = self.db.query(f"SELECT {COLUNAS} FROM produtos WHERE ativo = 1 ORDER BY id")
        return [_produto_dict(row) for row in rows]

    def buscar_por_id(self, produto_id):
        row = self.db.query_one(
            f"SELECT {COLUNAS} FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)
        )
        return _produto_dict(row) if row else None

    def criar(self, produto):
        cursor = self.db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (produto["nome"], produto["descricao"], produto["preco"], produto["estoque"], produto["categoria"]),
        )
        return cursor.lastrowid

    def atualizar(self, produto_id, produto):
        self.db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? "
            "WHERE id = ? AND ativo = 1",
            (produto["nome"], produto["descricao"], produto["preco"], produto["estoque"],
             produto["categoria"], produto_id),
        )

    def desativar(self, produto_id):
        self.db.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        clausulas, params = ["ativo = 1"], []
        if termo:
            clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clausulas.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clausulas.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clausulas.append("preco <= ?")
            params.append(preco_max)
        # Só texto fixo de cláusulas é concatenado; todo valor vai em params.
        filtro = " AND ".join(clausulas)
        rows = self.db.query(f"SELECT {COLUNAS} FROM produtos WHERE {filtro} ORDER BY id", params)
        return [_produto_dict(row) for row in rows]
