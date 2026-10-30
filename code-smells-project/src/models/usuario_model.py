import hmac

from werkzeug.security import check_password_hash, generate_password_hash

TIPO_ADMIN = "admin"
TIPO_CLIENTE = "cliente"

_PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def _to_public_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def _to_login_dict(row):
    return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}


class UsuarioModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        rows = self.db.connection.execute("SELECT * FROM usuarios").fetchall()
        return [_to_public_dict(row) for row in rows]

    def buscar_por_id(self, usuario_id):
        row = self.db.connection.execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return _to_public_dict(row) if row else None

    def email_existe(self, email):
        row = self.db.connection.execute(
            "SELECT 1 FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        return row is not None

    def criar(self, nome, email, senha, tipo=TIPO_CLIENTE):
        conn = self.db.connection
        with conn:
            cur = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
        return cur.lastrowid

    def autenticar(self, email, senha):
        """Devolve o usuário quando a senha confere; senhas legadas em texto puro são re-hasheadas."""
        row = self.db.connection.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        if row is None or not row["senha"]:
            return None
        armazenada = row["senha"]
        if armazenada.startswith(_PREFIXOS_HASH):
            if not check_password_hash(armazenada, senha):
                return None
        else:
            if not hmac.compare_digest(armazenada.encode(), senha.encode()):
                return None
            conn = self.db.connection
            with conn:
                conn.execute(
                    "UPDATE usuarios SET senha = ? WHERE id = ?",
                    (generate_password_hash(senha), row["id"]),
                )
        return _to_login_dict(row)
