import logging
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

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

SEED_PRODUTOS = (
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

# Credenciais de demonstração documentadas no README; gravadas sempre como hash.
SEED_USUARIOS = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)

HASH_PREFIXES = ("scrypt:", "pbkdf2:")


class Database:
    """Guarda só a configuração; cada requisição recebe a sua própria conexão."""

    def __init__(self, path):
        self.path = path

    def connect(self, read_only=False):
        if read_only:
            conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        else:
            conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def connection(self):
        if "db" not in g:
            g.db = self.connect()
        return g.db

    def close(self, _exc=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    def init_schema(self):
        conn = self.connect()
        try:
            for ddl in SCHEMA:
                conn.execute(ddl)
            conn.commit()
            if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                    SEED_PRODUTOS,
                )
                conn.executemany(
                    "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                    [(n, e, generate_password_hash(s), t) for n, e, s, t in SEED_USUARIOS],
                )
                conn.commit()
            self._migrar_senhas_legadas(conn)
        finally:
            conn.close()

    @staticmethod
    def _migrar_senhas_legadas(conn):
        legadas = [
            row for row in conn.execute("SELECT id, senha FROM usuarios")
            if not (row["senha"] or "").startswith(HASH_PREFIXES)
        ]
        for row in legadas:
            conn.execute(
                "UPDATE usuarios SET senha = ? WHERE id = ?",
                (generate_password_hash(row["senha"] or ""), row["id"]),
            )
        if legadas:
            conn.commit()
            logger.info("Senhas em texto puro migradas para hash: %s usuário(s)", len(legadas))
