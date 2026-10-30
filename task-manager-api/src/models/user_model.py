from werkzeug.security import check_password_hash, generate_password_hash

from src.database import db, utcnow

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
VALID_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=ROLE_USER)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

    def is_admin(self):
        return self.role == ROLE_ADMIN


def get_user(user_id):
    return db.session.get(User, user_id)


def get_user_by_email(email):
    return db.session.scalars(db.select(User).filter_by(email=email)).first()


def list_users():
    return db.session.scalars(db.select(User).order_by(User.id)).all()


def count_users():
    return db.session.scalar(db.select(db.func.count(User.id)))


def save(user):
    db.session.add(user)
    db.session.commit()
    return user


def delete_with_tasks(user):
    """Remove as tasks do usuário e o usuário no mesmo commit."""
    from src.models.task_model import Task

    db.session.execute(db.delete(Task).where(Task.user_id == user.id))
    db.session.delete(user)
    db.session.commit()
