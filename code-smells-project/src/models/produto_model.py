CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


class ProdutoModel:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def to_dict(row):
        return {campo: row[campo] for campo in CAMPOS}

    def listar(self):
        rows = self.db.connection().execute("SELECT * FROM produtos").fetchall()
        return [self.to_dict(row) for row in rows]

    def buscar_por_id(self, produto_id):
        row = self.db.connection().execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return self.to_dict(row) if row else None

    def criar(self, nome, descricao, preco, estoque, categoria):
        conn = self.db.connection()
        with conn:
            cursor = conn.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
        return cursor.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        conn = self.db.connection()
        with conn:
            conn.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )

    def deletar(self, produto_id):
        conn = self.db.connection()
        with conn:
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def possui_pedidos(self, produto_id):
        row = self.db.connection().execute(
            "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
        ).fetchone()
        return row is not None

    def buscar(self, termo, categoria=None, preco_min=None, preco_max=None):
        clausulas, params = ["1=1"], []
        if termo:
            clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clausulas.append("categoria = ?")
            params.append(categoria)
        if preco_min:
            clausulas.append("preco >= ?")
            params.append(preco_min)
        if preco_max:
            clausulas.append("preco <= ?")
            params.append(preco_max)
        rows = self.db.connection().execute(
            f"SELECT * FROM produtos WHERE {' AND '.join(clausulas)}", params
        ).fetchall()
        return [self.to_dict(row) for row in rows]
