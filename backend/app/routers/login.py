from fastapi import APIRouter, Depends

from app.schemas.auth_schema import LoginRequest, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(AuthService.inject),
) -> LoginResponse:
    return service.login(payload)
