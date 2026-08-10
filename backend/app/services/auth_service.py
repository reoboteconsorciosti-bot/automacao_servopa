from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, LoginResponse, LoginUserOut
from app.schemas.user_schema import verify_password


class AuthService:
    """Camada de negócio para autenticação — valida credenciais e orquestra o Repository."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    @staticmethod
    def inject(db: Session = Depends(get_db)) -> "AuthService":
        return AuthService(UserRepository(db))

    def _to_user_out(self, user: User) -> LoginUserOut:
        return LoginUserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            document=user.document,
            created_at=user.created_at.isoformat(),
        )

    def login(self, payload: LoginRequest) -> LoginResponse:
        user: Optional[User] = self.repo.get_by_email(payload.email)

        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha incorretos.",
            )

        return LoginResponse(
            ok=True,
            message="Login realizado com sucesso.",
            user=self._to_user_out(user),
        )
