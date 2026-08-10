from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Camada de persistência — acessa o Postgres via sessão SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> List[User]:
        return self.db.query(User).order_by(User.created_at.desc()).all()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
        document: str | None = None,
    ) -> User:
        now = datetime.utcnow()
        user = User(
            name=name,
            email=email.strip().lower(),
            document=document,
            password_hash=password_hash,
            created_at=now,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(
        self,
        user: User,
        *,
        name: str,
        email: str,
        document: str | None = None,
        password_hash: Optional[str] = None,
    ) -> User:
        user.name = name
        user.email = email.strip().lower()
        user.document = document
        if password_hash is not None:
            user.password_hash = password_hash
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
