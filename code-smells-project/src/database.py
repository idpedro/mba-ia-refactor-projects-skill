"""Acesso ao SQLite: uma conexão por requisição, schema, migrações idempotentes e seed."""
import logging
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from flask import g
from werkzeug.security import generate_password_hash

from src.models.constants import TIPO_ADMIN, TIPO_CLIENTE

logger = logging.getLogger(__name__)

HASH_PREFIXOS = ("scrypt:", "pbkdf2:")

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
)

PRODUTOS_SEED = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)


@dataclass(frozen=True)
class ContaSeed:
    nome: str
    tipo: str
    variavel: str
    email: str


# Contas criadas pelo seed. A senha nunca é literal: vem da variável ou é gerada e exibida uma vez.
CONTAS_SEED = (
    ContaSeed(nome="Admin", tipo=TIPO_ADMIN, variavel="ADMIN_PASSWORD", email="admin@loja.com"),
    ContaSeed(nome="João Silva", tipo=TIPO_CLIENTE, variavel="JOAO_PASSWORD", email="joao@email.com"),
    ContaSeed(nome="Maria Santos", tipo=TIPO_CLIENTE, variavel="MARIA_PASSWORD", email="maria@email.com"),
)


def _senha_da_conta(conta):
    valor = os.environ.get(conta.variavel)
    if valor:
        return valor
    gerada = secrets.token_urlsafe(12)
    logger.warning(
        "Senha gerada para %s: %s (exibida uma única vez; defina %s para escolher a senha)",
        conta.email, gerada, conta.variavel,
    )
    return gerada


class Database:
    def __init__(self, path):
        self.path = path

    def connect(self):
        conexao = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conexao.row_factory = sqlite3.Row
        return conexao

    # --- conexão por requisição -------------------------------------------------
    def connection(self):
        if "db_conexao" not in g:
            g.db_conexao = self.connect()
        return g.db_conexao

    def close(self, _exc=None):
        conexao = g.pop("db_conexao", None)
        if conexao is not None:
            conexao.close()

    def query(self, sql, params=()):
        return self.connection().execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        return self.connection().execute(sql, params).fetchone()

    def execute(self, sql, params=()):
        return self.connection().execute(sql, params)

    @contextmanager
    def transaction(self):
        """Transação de escrita serializada (BEGIN IMMEDIATE); rollback em qualquer falha."""
        conexao = self.connection()
        conexao.execute("BEGIN IMMEDIATE")
        try:
            yield conexao
        except BaseException:
            conexao.execute("ROLLBACK")
            raise
        conexao.execute("COMMIT")

    # --- boot -------------------------------------------------------------------
    def init(self):
        """Cria o schema, migra bancos existentes e faz o seed. Idempotente."""
        conexao = self.connect()
        try:
            conexao.execute("BEGIN IMMEDIATE")
            for ddl in SCHEMA:
                conexao.execute(ddl)
            self._dedup_emails(conexao)
            conexao.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email COLLATE NOCASE)"
            )
            self._migrar_senhas(conexao)
            self._seed(conexao)
            conexao.execute("COMMIT")
        except BaseException:
            conexao.execute("ROLLBACK")
            raise
        finally:
            conexao.close()

    @staticmethod
    def _dedup_emails(conexao):
        duplicados = conexao.execute(
            """
            SELECT u.id, u.email FROM usuarios u
            WHERE u.email IS NOT NULL AND EXISTS (
                SELECT 1 FROM usuarios o
                WHERE lower(o.email) = lower(u.email) AND o.id < u.id
            )
            """
        ).fetchall()
        for linha in duplicados:
            novo = f"duplicado-{linha['id']}+{linha['email']}"
            conexao.execute("UPDATE usuarios SET email = ? WHERE id = ?", (novo, linha["id"]))
            logger.warning("E-mail duplicado do usuário %s renomeado para %s", linha["id"], novo)

    @staticmethod
    def _migrar_senhas(conexao):
        contas = {conta.email: conta for conta in CONTAS_SEED}
        linhas = conexao.execute("SELECT id, email, senha FROM usuarios").fetchall()
        for linha in linhas:
            armazenada = linha["senha"] or ""
            if armazenada.startswith(HASH_PREFIXOS):
                continue
            conta = contas.get((linha["email"] or "").lower())
            if conta is not None:
                # Conta do seed original: a senha padrão conhecida nunca é mantida.
                nova = generate_password_hash(_senha_da_conta(conta))
                logger.warning("Senha legada da conta de seed %s substituída", conta.email)
            elif armazenada:
                nova = generate_password_hash(armazenada)
            else:
                nova = generate_password_hash(secrets.token_urlsafe(32))
            conexao.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (nova, linha["id"]))

    @staticmethod
    def _seed(conexao):
        if conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
            return
        conexao.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_SEED,
        )
        for conta in CONTAS_SEED:
            existe = conexao.execute(
                "SELECT 1 FROM usuarios WHERE email = ? COLLATE NOCASE", (conta.email,)
            ).fetchone()
            if existe:
                continue
            conexao.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (conta.nome, conta.email, generate_password_hash(_senha_da_conta(conta)), conta.tipo),
            )
        logger.info("Banco populado com dados de exemplo")
