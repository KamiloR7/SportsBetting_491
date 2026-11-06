from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.passwords import password_bytes


class PasswordInput(BaseModel):
    password: str = Field(
        min_length=1,
        max_length=128,
        repr=False,
    )

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value):
        password_bytes(value)
        return value


class UserRegister(PasswordInput):
    email: EmailStr
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=80,
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=120,
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        repr=False,
    )


class UserLogin(PasswordInput):
    email: EmailStr


class AssessmentNote(BaseModel):
    note: str = Field(
        min_length=1,
        max_length=500,
    )


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str]
    display_name: Optional[str]
    is_active: bool
    created_at: datetime