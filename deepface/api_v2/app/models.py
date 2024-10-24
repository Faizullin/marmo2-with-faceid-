import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import EmailStr
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


# Shared properties
class UserBase(SQLModel):
    __tablename__ = 'auth_user'
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    username: str


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: Union[str, None] = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: Union[EmailStr, None] = Field(
        default=None, max_length=255)  # type: ignore
    password: Union[str, None] = Field(
        default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: Union[str, None] = Field(default=None, max_length=255)
    email: Union[EmailStr, None] = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    # id: int = Field(default_factory=int, primary_key=True)
    id: Optional[int] = Field(default=None, primary_key=True)
    # id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # hashed_password: str
    # items: List["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    # id: uuid.UUID
    id: Union[uuid.UUID, int]


class UsersPublic(SQLModel):
    data: List[UserPublic]
    count: int


# Shared properties
class UserFaceIdBase(SQLModel):
    __tablename__ = 'user_face_id_userfaceid'
    model_path: str = Field(min_length=1, max_length=255)
    user_id: Optional[int] = Field(default=None, max_length=255)
    stats: Dict = Field(default_factory=dict, sa_column=Column(JSON))


class UserFaceIdCreate(UserFaceIdBase):
    pass


class UserFaceId(UserFaceIdBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # id: Optional[int] = Field(default=None, primary_key=True)
    # user: Optional[Union[User]] = Relationship(back_populates="face_id_list")


class UserFaceIdPublic(UserFaceIdBase):
    id: int
    user_id: int


class UserFaceIdListPublic(SQLModel):
    data: List[UserFaceIdPublic]
    count: int


# Shared properties
class OneTimeTokenBase(SQLModel):
    __tablename__ = 'users_onetimetoken'
    user_id: Optional[int] = Field(default=None, max_length=255)
    token: str
    created_at: datetime
    is_used: bool


class OneTimeToken(OneTimeTokenBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime  = Field(default_factory=datetime.utcnow, nullable=False)


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: Union[str, None] = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
