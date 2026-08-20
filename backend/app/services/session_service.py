"""
Sessão de login via cookie assinado e HttpOnly
================================================
Substitui a antiga abordagem de deixar o front-end guardar "quem está logado"
por conta própria (ex.: localStorage) por um cookie de sessão que o navegador
gerencia sozinho e que JavaScript nunca consegue ler nem escrever.

Por que HttpOnly resolve o pedido original:
  - Um cookie marcado HttpOnly é omitido inteiramente de `document.cookie` —
    não é "criptografado na tela", ele simplesmente não aparece lá. Isso vale
    mesmo que um ataque de XSS consiga rodar JavaScript arbitrário na página:
    `document.cookie` retorna os outros cookies (se houver), nunca este.
  - Como reforço adicional (caso o cookie vaze por outro caminho, ex.: log,
    proxy mal configurado), o valor não é o e-mail/id em texto puro: é uma
    string assinada (HMAC) por itsdangerous. Qualquer alteração no valor
    invalida a assinatura e a sessão é rejeitada — o "modificado" do pedido
    original também fica coberto.

Não usamos JWT (nem uma tabela de sessões no Postgres) de propósito: o projeto
já não tem nenhuma infraestrutura de auth além de checar e-mail/senha, e um
token assinado com itsdangerous é suficiente para esse volume de usuários,
sem introduzir uma dependência nova pesada nem estado adicional no banco.
"""

from __future__ import annotations

import os
from typing import Optional, TypedDict

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE_NAME = "servopa_session"

# Duração da sessão em segundos (padrão: 12 horas). Ajustável via .env sem tocar no código.
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(12 * 60 * 60)))

# Chave usada para assinar o cookie. Em produção, defina SECRET_KEY no ambiente
# (EasyPanel) — sem ela, qualquer pessoa com acesso ao código poderia forjar
# sessões. O valor abaixo é só uma rede de segurança para não quebrar o dev
# local caso alguém esqueça de definir a variável.
_SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not _SECRET_KEY:
    _SECRET_KEY = "dev-only-insecure-secret-key-troque-via-SECRET_KEY"

_serializer = URLSafeTimedSerializer(_SECRET_KEY, salt="servopa-session")


class SessionPayload(TypedDict):
    userId: int
    email: str
    name: str


def create_session_cookie_value(*, user_id: int, email: str, name: str) -> str:
    """Gera o valor assinado que vai dentro do cookie HttpOnly."""
    payload: SessionPayload = {"userId": user_id, "email": email, "name": name}
    return _serializer.dumps(payload)


def read_session_cookie_value(value: Optional[str]) -> Optional[SessionPayload]:
    """Valida a assinatura e a expiração do cookie. Retorna None se ausente,
    adulterado ou expirado — nunca lança exceção para o chamador."""
    if not value:
        return None
    try:
        return _serializer.loads(value, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
