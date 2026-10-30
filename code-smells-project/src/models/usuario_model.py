import hmac

from werkzeug.security import check_password_hash, generate_password_hash

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_SESSAO = ("id", "nome", "email", "tipo")
TIPO_PADRAO = "cliente"
_PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def usuario_to_dict(row, campos=CAMPOS_PUBLICOS):
    """Public serializer: never includes `senha`."""
    return {campo: row[campo] for campo in campos}


class UsuarioModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        rows = self.db.connection().execute("SELECT * FROM usuarios").fetchall()
        return [usuario_to_dict(row) for row in rows]

    def buscar_por_id(self, usuario_id):
        row = self.db.connection().execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return usuario_to_dict(row) if row else None

    def criar(self, nome, email, senha, tipo=TIPO_PADRAO):
        conn = self.db.connection()
        with conn:
            cur = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
        return cur.lastrowid

    def autenticar(self, email, senha):
        """Return the session view of the user when the password matches, else None."""
        conn = self.db.connection()
        rows = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchall()
        for row in rows:
            armazenada = row["senha"] or ""
            if armazenada.startswith(_PREFIXOS_HASH):
                if check_password_hash(armazenada, senha):
                    return usuario_to_dict(row, CAMPOS_SESSAO)
            elif hmac.compare_digest(armazenada.encode(), senha.encode()):
                # Legacy plaintext row from an old loja.db: upgrade it on first login.
                with conn:
                    conn.execute(
                        "UPDATE usuarios SET senha = ? WHERE id = ?",
                        (generate_password_hash(senha), row["id"]),
                    )
                return usuario_to_dict(row, CAMPOS_SESSAO)
        return None

    def contar(self):
        return self.db.connection().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
