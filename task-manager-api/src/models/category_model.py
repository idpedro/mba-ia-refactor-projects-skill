from src.database import db, utcnow

DEFAULT_COLOR = "#000000"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": str(self.created_at),
        }


def get_category(category_id):
    return db.session.get(Category, category_id)


def list_categories():
    return db.session.scalars(db.select(Category).order_by(Category.id)).all()


def count_categories():
    return db.session.scalar(db.select(db.func.count(Category.id)))


def save(category):
    db.session.add(category)
    db.session.commit()
    return category


def delete_detaching_tasks(category):
    """Desvincula as tasks e remove a categoria na mesma transação (sem category_id órfão)."""
    from src.models.task_model import Task

    db.session.execute(db.update(Task).where(Task.category_id == category.id).values(category_id=None))
    db.session.delete(category)
    db.session.commit()
