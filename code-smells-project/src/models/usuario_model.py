"""Persistência de usuários. A senha só existe como hash e nunca sai do model."""
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from src.errors import ConflictError
from src.models.constants import TIPO_CLIENTE

COLUNAS_PUBLICAS = "id, nome, email, tipo, criado_em"


def _usuario_dict(row, incluir_criado_em=True):
    dados = {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    if incluir_criado_em:
        dados["criado_em"] = row["criado_em"]
    return dados


class UsuarioModel:
    def __init__(self, db):
        self.db = db

    def listar(self):
        rows = self.db.query(f"SELECT {COLUNAS_PUBLICAS} FROM usuarios ORDER BY id")
        return [_usuario_dict(row) for row in rows]

    def buscar_por_id(self, usuario_id):
        row = self.db.query_one(f"SELECT {COLUNAS_PUBLICAS} FROM usuarios WHERE id = ?", (usuario_id,))
        return _usuario_dict(row) if row else None

    def criar(self, nome, email, senha, tipo=TIPO_CLIENTE):
        try:
            cursor = self.db.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc):
                raise ConflictError("Email já cadastrado") from exc
            raise
        return cursor.lastrowid

    def autenticar(self, email, senha):
        row = self.db.query_one(
            "SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ? COLLATE NOCASE", (email,)
        )
        if row is None or not row["senha"] or not check_password_hash(row["senha"], senha):
            return None
        return _usuario_dict(row, incluir_criado_em=False)
