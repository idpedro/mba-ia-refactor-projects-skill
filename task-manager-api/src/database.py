"""Objeto do banco e migrações idempotentes executadas no boot."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

# create_all() só cria tabelas novas; estas instruções atualizam bancos já existentes
# e podem rodar a cada boot sem efeito colateral.
SCHEMA_MIGRATIONS = (
    # Unicidade de e-mail sem diferenciar maiúsculas, garantida pelo banco.
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower ON users (lower(email))",
    # Tasks que apontam para categorias inexistentes ficam sem categoria.
    "UPDATE tasks SET category_id = NULL "
    "WHERE category_id IS NOT NULL AND category_id NOT IN (SELECT id FROM categories)",
)


def init_database(app):
    db.init_app(app)
    with app.app_context():
        from src import models  # noqa: F401  registra as tabelas no metadata

        db.create_all()
        for statement in SCHEMA_MIGRATIONS:
            db.session.execute(text(statement))
        db.session.commit()
