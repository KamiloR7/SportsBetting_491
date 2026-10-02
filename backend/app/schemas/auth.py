from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(default=None, min_length=3, max_length=80)
    display_name: Optional[str] = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str]
    display_name: Optional[str]
    is_active: bool
    created_at: datetime