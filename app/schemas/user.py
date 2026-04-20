from datetime import datetime
from app.models.user import UserRole
from pydantic import BaseModel, ConfigDict, Field
from pydantic import field_validator
import re


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_]+", value):
            raise ValueError("Username can only contain letters, numbers, and underscore")
        return value


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(UserRegister):
    role: UserRole = UserRole.USER


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    is_active: bool
    role: UserRole
    created_at: datetime