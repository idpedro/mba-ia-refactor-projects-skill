from src.controllers.validators import validate_category
from src.errors import NotFoundError
from src.models import category_model, task_model
from src.models.category_model import DEFAULT_COLOR, Category
from src.models.task_model import Task


class CategoryController:
    def list_all(self):
        task_counts = task_model.count_tasks_by(Task.category_id)
        result = []
        for category in category_model.list_categories():
            data = category.to_dict()
            data["task_count"] = task_counts.get(category.id, 0)
            result.append(data)
        return result

    def create(self, data):
        fields = validate_category(data)
        fields.setdefault("color", DEFAULT_COLOR)
        return category_model.save(Category(**fields)).to_dict()

    def update(self, category_id, data):
        category = self._find(category_id)
        for name, value in validate_category(data, partial=True).items():
            setattr(category, name, value)
        return category_model.save(category).to_dict()

    def delete(self, category_id):
        category_model.delete_detaching_tasks(self._find(category_id))

    @staticmethod
    def _find(category_id):
        category = category_model.get_category(category_id)
        if category is None:
            raise NotFoundError("Categoria não encontrada")
        return category
