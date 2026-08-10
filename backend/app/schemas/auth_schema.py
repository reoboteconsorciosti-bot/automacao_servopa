from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=255)


class LoginUserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    document: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    ok: bool
    message: str
    user: Optional[LoginUserOut] = None
