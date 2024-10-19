import uuid

from pydantic import BaseModel

from .base import UserBase, BookBase

class RegisterPayload(UserBase):
    password: str  # 明文


class LoginPayload(BaseModel):
    username: str
    password: str


class UserInfoResp(UserBase):
    id: uuid.UUID


class BookAddPayload(BookBase):
    pass


class BookQueryPayload(BaseModel):
    name: str | None = None
    isbn: str | None = None
    author: str | None = None
    publisher: str | None = None
    desc: str | None = None
    extra: str | None = None


class BookModifyPayload(BookQueryPayload):
    id: uuid.UUID
    cover: str | None = None
