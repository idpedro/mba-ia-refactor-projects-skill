import logging

from src.controllers import validators
from src.database import db
from src.middlewares.error_handler import NotFoundError

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND = "Categoria não encontrada"


class CategoryController:
    def __init__(self, category_model, task_model):
        self.categories = category_model
        self.tasks = task_model

    def list_categories(self):
        task_counts = self.tasks.count_by_category()
        return [
            {**category.to_dict(), "task_count": task_counts.get(category.id, 0)}
            for category in self.categories.all()
        ]

    def create_category(self, data):
        fields = validators.validate_new_category(data)
        category = self.categories(**fields)
        db.session.add(category)
        db.session.commit()
        return category.to_dict()

    def update_category(self, category_id, data):
        category = self._find(category_id)
        for field, value in validators.validate_category_changes(data).items():
            setattr(category, field, value)
        db.session.commit()
        return category.to_dict()

    def delete_category(self, category_id):
        category = self._find(category_id)
        self.tasks.clear_category(category_id)  # sem tasks órfãs (decisão 7)
        db.session.delete(category)
        db.session.commit()
        logger.info("Categoria deletada id=%s", category_id)

    def _find(self, category_id):
        category = self.categories.get(category_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND)
        return category
