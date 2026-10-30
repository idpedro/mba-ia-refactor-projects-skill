import hashlib
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from src.database import db, utcnow

ROLE_USER, ROLE_ADMIN, ROLE_MANAGER = "user", "admin", "manager"
USER_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
DEFAULT_ROLE = ROLE_USER
MIN_PASSWORD_LENGTH = 4
EMAIL_PATTERN = r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"

_LEGACY_HASH_LENGTH = 32  # hex digest do formato antigo (decisão 2)


def _is_legacy_hash(stored):
    return len(stored) == _LEGACY_HASH_LENGTH and all(ch in "0123456789abcdef" for ch in stored)


def _legacy_digest(raw):
    # Usado só para VERIFICAR hashes gravados no formato antigo; nunca para gravar.
    return hashlib.md5(raw.encode()).hexdigest()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        """Representação pública: nunca inclui o hash da senha (decisão 1)."""
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
        if _is_legacy_hash(self.password):
            return hmac.compare_digest(self.password, _legacy_digest(raw_password))
        return check_password_hash(self.password, raw_password)

    def needs_rehash(self):
        return _is_legacy_hash(self.password)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    @classmethod
    def get(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def all(cls):
        return db.session.scalars(db.select(cls).order_by(cls.id)).all()

    @classmethod
    def find_by_email(cls, email):
        return db.session.scalars(db.select(cls).where(cls.email == email)).first()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(db.func.count(cls.id)))
