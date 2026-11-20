"""Script para popular o banco com dados iniciais.

As senhas das contas vêm de SEED_ADMIN_PASSWORD / SEED_USER_PASSWORD; sem elas, cada
conta recebe uma senha aleatória, exibida uma única vez no log abaixo.
"""
import logging
from datetime import timedelta

from sqlalchemy import delete

from src.app import create_app
from src.config.settings import Settings
from src.constants import (
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_USER,
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
)
from src.database import db
from src.models import Category, Task, User
from src.models.base import utcnow
from src.services.credential_service import seed_password

logger = logging.getLogger('seed')

USERS = (
    ('admin', 'João Silva', 'joao@email.com', ROLE_ADMIN),
    ('maria', 'Maria Santos', 'maria@email.com', ROLE_USER),
    ('pedro', 'Pedro Oliveira', 'pedro@email.com', ROLE_MANAGER),
)

CATEGORIES = (
    ('backend', 'Backend', 'Tarefas de backend', '#3498db'),
    ('frontend', 'Frontend', 'Tarefas de frontend', '#2ecc71'),
    ('devops', 'DevOps', 'Tarefas de infraestrutura', '#e74c3c'),
    ('bug', 'Bug', 'Correção de bugs', '#e67e22'),
)

# (título, descrição, status, prioridade, dono, categoria, prazo em dias a partir de hoje, tags)
TASKS = (
    ('Implementar autenticação JWT', 'Adicionar autenticação real com JWT', STATUS_PENDING, 1, 'admin', 'backend', -3, None),
    ('Criar tela de login', 'Tela de login responsiva', STATUS_IN_PROGRESS, 2, 'maria', 'frontend', 5, None),
    ('Configurar CI/CD', 'Pipeline com GitHub Actions', STATUS_DONE, 2, 'pedro', 'devops', None, 'devops,ci,github'),
    ('Corrigir bug no filtro de busca', 'Filtro não funciona com caracteres especiais', STATUS_PENDING, 1, 'admin', 'bug', -1, None),
    ('Adicionar paginação na API', 'Endpoints retornam todos os registros', STATUS_PENDING, 3, 'admin', 'backend', 10, None),
    ('Escrever testes unitários', 'Cobertura mínima de 80%', STATUS_PENDING, 2, 'maria', 'backend', None, None),
    ('Documentar API com Swagger', 'Gerar documentação automática', STATUS_CANCELLED, 4, 'pedro', 'backend', None, None),
    ('Refatorar models', 'Melhorar organização dos models', STATUS_IN_PROGRESS, 3, 'maria', 'backend', None, 'refactor,tech-debt'),
    ('Configurar monitoramento', 'Prometheus + Grafana', STATUS_PENDING, 4, 'pedro', 'devops', 20, None),
    ('Melhorar validações de input', 'Usar marshmallow ou pydantic', STATUS_PENDING, 3, 'admin', 'backend', None, 'improvement,validation'),
)


def seed_data(app, settings=Settings):
    with app.app_context():
        for model in (Task, User, Category):
            db.session.execute(delete(model))
        db.session.commit()

        users = {}
        for key, name, email, role in USERS:
            user = User(name=name, email=email, role=role)
            user.set_password(seed_password(settings, role, email))
            users[key] = user
        categories = {
            key: Category(name=name, description=description, color=color)
            for key, name, description, color in CATEGORIES
        }
        db.session.add_all([*users.values(), *categories.values()])

        now = utcnow()
        for title, description, status, priority, owner, category, due_in_days, tags in TASKS:
            db.session.add(Task(
                title=title,
                description=description,
                status=status,
                priority=priority,
                user=users[owner],
                category=categories[category],
                due_date=now + timedelta(days=due_in_days) if due_in_days is not None else None,
                tags=tags,
            ))
        db.session.commit()

        logger.info('Seed concluído com sucesso!')
        logger.info('  %s usuários', User.count())
        logger.info('  %s categorias', Category.count())
        logger.info('  %s tasks', Task.count())


if __name__ == '__main__':
    seed_data(create_app())
