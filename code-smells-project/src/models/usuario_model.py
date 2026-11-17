CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
TIPO_CLIENTE = "cliente"
TIPO_ADMIN = "admin"


class UsuarioModel:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def to_dict(row):
        """Serializador público: nunca inclui a senha nem o hash."""
        return {campo: row[campo] for campo in CAMPOS_PUBLICOS}

    def listar(self):
        rows = self.db.connection().execute("SELECT * FROM usuarios").fetchall()
        return [self.to_dict(row) for row in rows]

    def buscar_por_id(self, usuario_id):
        row = self.db.connection().execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return self.to_dict(row) if row else None

    def buscar_credenciais(self, email):
        """Linha completa (com hash) usada só pela verificação de login."""
        return self.db.connection().execute(
            "SELECT * FROM usuarios WHERE email = ? ORDER BY id LIMIT 1", (email,)
        ).fetchone()

    def criar(self, nome, email, senha_hash, tipo=TIPO_CLIENTE):
        conn = self.db.connection()
        with conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, senha_hash, tipo),
            )
        return cursor.lastrowid
