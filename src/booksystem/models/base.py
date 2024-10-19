import re
from typing import Annotated
from enum import Enum

from pydantic import (
    StringConstraints,
    field_validator,
)
from sqlmodel import Field, SQLModel


BAD_LETTER_PATTERN = re.compile(r"[<>{}\[\]\\]")


class Gender(Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class UserBase(SQLModel):
    username: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            pattern=r"^[a-zA-Z0-9_\-]+$",
            max_length=20,
            min_length=3,
        ),
    ] = Field(unique=True)
    nickname: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=20, min_length=1)
    ]
    gender: Gender = Field(default=Gender.UNKNOWN)
    age: int = Field(ge=0)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str):
        if BAD_LETTER_PATTERN.search(v):
            raise ValueError("Bad letter detected")
        return v


class BookBase(SQLModel):
    name: str
    isbn: Annotated[str, StringConstraints(strip_whitespace=True)]
    author: str
    publisher: str
    desc: str
    cover: str
    extra: str = ""

    @field_validator("isbn", mode="before")
    @classmethod
    def validate_isbn(cls, v: str):
        if isinstance(v, str):
            v = v.replace("-", "").strip()
            if len(v) != 13 or not v.isdigit():
                raise ValueError("ISBN should be a 13-digit number")
        return v
