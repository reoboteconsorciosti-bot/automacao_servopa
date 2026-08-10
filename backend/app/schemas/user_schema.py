from __future__ import annotations

import hashlib
import os
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def hash_password(raw: str) -> str:
    """
    Hash simples com PBKDF2-HMAC-SHA256 + salt aleatório.
    Produção recomendada: instalar passlib[bcrypt] e trocar por bcrypt.
    """
    salt = os.urandom(16)
    pwdhash = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256${salt.hex()}${pwdhash.hex()}"


def verify_password(raw: str, stored: str) -> bool:
    try:
        algo, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        computed = hashlib.pbkdf2_hmac(
            "sha256", raw.encode("utf-8"), salt, 200_000
        )
        return computed == expected
    except Exception:
        return False


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    document: str | None = Field(default=None, max_length=32)


class UserCreate(UserBase):
    password: str = Field(min_length=4, max_length=255)


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    document: str | None = Field(default=None, max_length=32)
    password: str | None = Field(default=None, min_length=4, max_length=255)


class UserOut(UserBase):
    id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)
