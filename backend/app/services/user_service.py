from typing import List, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserOut, UserUpdate, hash_password


class UserService:
    """Camada de negócio — valida regras e orquestra o Repository."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    @staticmethod
    def inject(db: Session = Depends(get_db)) -> "UserService":
        return UserService(UserRepository(db))

    def _to_out(self, user: User) -> UserOut:
        return UserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            document=user.document,
            created_at=user.created_at.isoformat(),
        )

    def list_users(self) -> List[UserOut]:
        return [self._to_out(u) for u in self.repo.list_all()]

    def get_user_or_404(self, user_id: int) -> UserOut:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
        return self._to_out(user)

    def _ensure_unique_email(self, email: str, ignore_id: Optional[int] = None) -> None:
        existing = self.repo.get_by_email(email)
        if existing is None:
            return
        if ignore_id is None or existing.id != ignore_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Este e-mail já está cadastrado.",
            )

    def create_user(self, payload: UserCreate) -> UserOut:
        self._ensure_unique_email(payload.email)
        user = self.repo.create(
            name=payload.name,
            email=payload.email,
            document=payload.document,
            password_hash=hash_password(payload.password),
        )
        return self._to_out(user)

    def update_user(self, user_id: int, payload: UserUpdate) -> UserOut:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
        self._ensure_unique_email(payload.email, ignore_id=user.id)
        pwd_hash: Optional[str] = None
        if payload.password:
            pwd_hash = hash_password(payload.password)
        updated = self.repo.update(
            user,
            name=payload.name,
            email=payload.email,
            document=payload.document,
            password_hash=pwd_hash,
        )
        return self._to_out(updated)

    def delete_user(self, user_id: int) -> None:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
        self.repo.delete(user)
