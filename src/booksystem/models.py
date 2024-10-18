import random
import re
import uuid
from typing import Annotated
from enum import Enum

from pydantic import (
    UUID4,
    AnyUrl,
    BaseModel,
    Field,
    Json,
    StringConstraints,
    field_validator,
)


def generate_salt():
    table = list("1145141919810____")
    random.shuffle(table)
    return "".join(table)


BAD_LETTER_PATTERN = re.compile(r"[<>{}\[\]\\]")


class Gender(Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class UserModel(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    username: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            pattern=r"^[a-zA-Z0-9_\-]+$",
            max_length=20,
            min_length=3,
        ),
    ]
    nickname: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=20, min_length=1)
    ]
    gender: Gender = Field(default=Gender.UNKNOWN)
    salt: str = Field(default_factory=generate_salt)
    password: Annotated[
        str, StringConstraints(pattern=r"^[0-9a-f]+$", max_length=64, min_length=64)
    ]

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str):
        if BAD_LETTER_PATTERN.search(v):
            raise ValueError("Bad letter detected")
        return v


class BookModel(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    name: str
    isbn: Annotated[str, StringConstraints(strip_whitespace=True)]
    author: str
    publisher: str
    desc: str
    cover: AnyUrl
    extra: Json = "{}"

    @field_validator("isbn", mode="before")
    @classmethod
    def validate_isbn(cls, v: str):
        if isinstance(v, str):
            v = v.replace("-", "").strip()
            if len(v) != 13 or not v.isdigit():
                raise ValueError("ISBN should be a 13-digit number")
        return v


class OwnedBookModel(BookModel):
    owner: UUID4


class ImageModel(BaseModel):
    id: UUID4
    data: bytes


if __name__ == "__main__":
    # just test ww
    import hashlib

    u = UserModel(
        username="lemon",
        nickname="LemonyNingmeng",
        password=hashlib.sha256().hexdigest(),
    )
    b = BookModel(
        name="0721大师的自我修养",
        isbn="114-514-1919-81-0",
        author="Ayachi Nene",
        publisher="Yuzusoft",
        desc="0721，爽！0721，爽！0721，爽！0721，爽！0721，爽！0721，爽！0721，爽！0721，爽！0721，爽！",
        cover="https://moegirl.icu/media/Ayachi_Nene.png",
    )
