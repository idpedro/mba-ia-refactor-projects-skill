import logging

from src.controllers.validators import validate_category_payload
from src.errors import NotFoundError

logger = logging.getLogger(__name__)


class CategoryController:
    def __init__(self, categories):
        self.categories = categories

    def list(self):
        return [
            dict(category.to_dict(), task_count=task_count)
            for category, task_count in self.categories.list_with_task_counts()
        ]

    def create(self, data):
        fields = validate_category_payload(data, creating=True)
        category = self.categories(**fields)
        category.save()
        logger.info('Categoria criada id=%s', category.id)
        return category.to_dict()

    def update(self, category_id, data):
        category = self._get_or_404(category_id)
        fields = validate_category_payload(data, creating=False)
        for name, value in fields.items():
            setattr(category, name, value)
        category.save()
        return category.to_dict()

    def delete(self, category_id):
        category = self._get_or_404(category_id)
        category.delete_detaching_tasks()
        logger.info('Categoria deletada id=%s', category_id)
        return {'message': 'Categoria deletada'}

    def _get_or_404(self, category_id):
        category = self.categories.get(category_id)
        if category is None:
            raise NotFoundError('Categoria não encontrada')
        return category
