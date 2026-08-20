import os

from fastapi import APIRouter, Depends, Request, Response

from app.schemas.auth_schema import LoginRequest, LoginResponse
from app.services.auth_service import AuthService
from app.services.session_service import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_cookie_value,
    read_session_cookie_value,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# "Secure" (cookie só trafega em HTTPS) segue o mesmo sinal de DEBUG usado no
# resto do backend por padrão: desligado em dev (permite testar em
# http://localhost), ligado em produção. Pode ser forçado via COOKIE_SECURE.
_cookie_secure_env = os.getenv("COOKIE_SECURE", "").strip().lower()
if _cookie_secure_env in ("1", "true", "yes"):
    COOKIE_SECURE = True
elif _cookie_secure_env in ("0", "false", "no"):
    COOKIE_SECURE = False
else:
    COOKIE_SECURE = os.getenv("DEBUG", "1") != "1"

# "lax" cobre o caso comum (front-end e API no mesmo domínio raiz, ex.:
# localhost:3000 -> localhost:8000). Se front-end e API ficarem em domínios
# totalmente diferentes em produção, ajuste para "none" (exige COOKIE_SECURE=true).
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()


def _set_session_cookie(response: Response, *, user_id: int, email: str, name: str) -> None:
    token = create_session_cookie_value(user_id=user_id, email=email, name=name)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,  # nunca aparece em document.cookie, nem é acessível via JS
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    service: AuthService = Depends(AuthService.inject),
) -> LoginResponse:
    result = service.login(payload)
    if result.ok and result.user:
        _set_session_cookie(
            response,
            user_id=result.user.id,
            email=result.user.email,
            name=result.user.name,
        )
    return result


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"ok": True, "message": "Sessão encerrada."}


@router.get("/me")
def me(request: Request) -> dict:
    """Permite ao front-end saber quem está logado sem precisar guardar isso
    por conta própria — o cookie HttpOnly não pode ser lido via JavaScript,
    então esta é a única forma de o front-end confirmar a sessão atual."""
    session = read_session_cookie_value(request.cookies.get(SESSION_COOKIE_NAME))
    if session is None:
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": {
            "id": session["userId"],
            "email": session["email"],
            "name": session["name"],
        },
    }
