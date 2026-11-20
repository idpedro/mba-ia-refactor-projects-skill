from src.controllers.validators import validate_category
from src.database import db
from src.errors import NotFoundError
from src.models import Category, Task


class CategoryController:
    def list(self):
        return [
            {**category.to_dict(), 'task_count': task_count}
            for category, task_count in Category.list_with_task_counts()
        ]

    def create(self, data):
        category = Category(**validate_category(data))
        db.session.add(category)
        db.session.commit()
        return category.to_dict()

    def update(self, category_id, data):
        category = self._existing(category_id)
        for name, value in validate_category(data, partial=True).items():
            setattr(category, name, value)
        db.session.commit()
        return category.to_dict()

    def delete(self, category_id):
        category = self._existing(category_id)
        # Mesma transação: as tasks perdem a categoria antes de ela ser apagada.
        Task.clear_category(category_id)
        db.session.delete(category)
        db.session.commit()
        return {'message': 'Categoria deletada'}

    @staticmethod
    def _existing(category_id):
        category = Category.get(category_id)
        if category is None:
            raise NotFoundError('Categoria não encontrada')
        return category
