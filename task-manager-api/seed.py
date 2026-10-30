"""Script para popular o banco com dados iniciais"""
from datetime import timedelta

from src.app import create_app
from src.database import db, utcnow
from src.models import Category, Task, User
from src.models.user_model import ROLE_ADMIN, ROLE_MANAGER, ROLE_USER

USERS = [
    ("João Silva", "joao@email.com", "1234", ROLE_ADMIN),
    ("Maria Santos", "maria@email.com", "abcd", ROLE_USER),
    ("Pedro Oliveira", "pedro@email.com", "pass", ROLE_MANAGER),
]

CATEGORIES = [
    ("Backend", "Tarefas de backend", "#3498db"),
    ("Frontend", "Tarefas de frontend", "#2ecc71"),
    ("DevOps", "Tarefas de infraestrutura", "#e74c3c"),
    ("Bug", "Correção de bugs", "#e67e22"),
]


def build_tasks(users, categories):
    joao, maria, pedro = users
    backend, frontend, devops, bug = categories
    now = utcnow()
    return [
        {"title": "Implementar autenticação JWT", "description": "Adicionar autenticação real com JWT", "status": "pending", "priority": 1, "user": joao, "category": backend, "due_date": now - timedelta(days=3)},
        {"title": "Criar tela de login", "description": "Tela de login responsiva", "status": "in_progress", "priority": 2, "user": maria, "category": frontend, "due_date": now + timedelta(days=5)},
        {"title": "Configurar CI/CD", "description": "Pipeline com GitHub Actions", "status": "done", "priority": 2, "user": pedro, "category": devops, "tags": "devops,ci,github"},
        {"title": "Corrigir bug no filtro de busca", "description": "Filtro não funciona com caracteres especiais", "status": "pending", "priority": 1, "user": joao, "category": bug, "due_date": now - timedelta(days=1)},
        {"title": "Adicionar paginação na API", "description": "Endpoints retornam todos os registros", "status": "pending", "priority": 3, "user": joao, "category": backend, "due_date": now + timedelta(days=10)},
        {"title": "Escrever testes unitários", "description": "Cobertura mínima de 80%", "status": "pending", "priority": 2, "user": maria, "category": backend},
        {"title": "Documentar API com Swagger", "description": "Gerar documentação automática", "status": "cancelled", "priority": 4, "user": pedro, "category": backend},
        {"title": "Refatorar models", "description": "Melhorar organização dos models", "status": "in_progress", "priority": 3, "user": maria, "category": backend, "tags": "refactor,tech-debt"},
        {"title": "Configurar monitoramento", "description": "Prometheus + Grafana", "status": "pending", "priority": 4, "user": pedro, "category": devops, "due_date": now + timedelta(days=20)},
        {"title": "Melhorar validações de input", "description": "Usar marshmallow ou pydantic", "status": "pending", "priority": 3, "user": joao, "category": backend, "tags": "improvement,validation"},
    ]


def seed_data():
    app = create_app()
    with app.app_context():
        db.session.execute(db.delete(Task))
        db.session.execute(db.delete(User))
        db.session.execute(db.delete(Category))
        db.session.commit()

        users = []
        for name, email, password, role in USERS:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            users.append(user)
        categories = [Category(name=name, description=description, color=color) for name, description, color in CATEGORIES]
        db.session.add_all(users + categories)
        db.session.commit()

        for fields in build_tasks(users, categories):
            user, category = fields.pop("user"), fields.pop("category")
            db.session.add(Task(user_id=user.id, category_id=category.id, **fields))
        db.session.commit()

        print("Seed concluído com sucesso!")
        print(f"  {db.session.scalar(db.select(db.func.count(User.id)))} usuários")
        print(f"  {db.session.scalar(db.select(db.func.count(Category.id)))} categorias")
        print(f"  {db.session.scalar(db.select(db.func.count(Task.id)))} tasks")


if __name__ == "__main__":
    seed_data()
