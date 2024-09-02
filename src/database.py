import sqlite3
import json
from typing import TypedDict, TypeAlias, Union, List, Dict, Unpack, Any, Type, Mapping

from rwlock import ReadWriteLock


_JSONType: TypeAlias = Union[
    str, int, float, bool, None, Dict[str, "_JSONType"], List["_JSONType"]
]


class _RequiredBookInfo(TypedDict):
    """
    图书信息结构定义
    """

    title: str
    isbn: str  # ISBN 13
    author: str
    publisher: str
    desc: str
    cover: str
    price: float
    extra: _JSONType


BookInfo: TypeAlias = _RequiredBookInfo


class PartialBookInfo(_RequiredBookInfo, total=False):
    pass


class QueriedBookInfo(_RequiredBookInfo, total=True):
    id: int


class PartialQueriedBookInfo(QueriedBookInfo, total=False):
    pass


_TYPE_TO_SQLITE_TYPE_MAP = {
    str: "TEXT",
    int: "INTEGER",
    float: "REAL",
    None: "NULL",
    type(None): "NULL",
    _JSONType: "TEXT",
}


def type_to_sqlitetype(t: Type) -> str | None:
    return _TYPE_TO_SQLITE_TYPE_MAP.get(t)


def verify_keys(d: Mapping, dt: Type[Mapping], fullmatch=False):
    anno = getattr(dt, "__annotations__", {})
    if fullmatch:
        assert set(d.keys()) == set(anno.keys()), "keys not equal"
    for k in d.keys():
        assert k in anno, f"unexpected key: {k}"


class BookDB:
    """
    图书数据库对象
    """

    def __init__(self, dbpath: str) -> None:
        self._dbpath = dbpath
        self._lock = ReadWriteLock()
        self.create_table()

    def _get_connection(self):
        return sqlite3.connect(self._dbpath)

    def create_table(self):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    {},
                    id INTEGER PRIMARY KEY AUTOINCREMENT
                )
                """.format(
                    ", ".join(
                        [
                            f"{k} {type_to_sqlitetype(v)} NOT NULL"
                            for k, v in _RequiredBookInfo.__annotations__.items()
                        ]
                    )
                )
            )

    def add(self, book: BookInfo):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO books ({})
                VALUES ({})
                """.format(
                    ", ".join(_RequiredBookInfo.__annotations__.keys()),
                    ", ".join(["?"] * len(_RequiredBookInfo.__annotations__)),
                ),
                [
                    (json.dumps(book[k]) if v == _JSONType else book[k])  # type: ignore[literal-required]
                    for k, v in _RequiredBookInfo.__annotations__.items()
                ],
            )

    def delete(self, book_id: int):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))

    def modify(self, book_id: int, **info: Unpack[PartialBookInfo]):
        if not info:
            return
        verify_keys(info, PartialBookInfo, fullmatch=False)
        update_query = "UPDATE books SET "
        update_values = []
        for key, value in info.items():
            update_query += f"{key} = ?, "
            update_values.append(
                (
                    json.dumps(value)
                    if PartialBookInfo.__annotations__[key] == _JSONType
                    else value
                )
            )
        update_query = update_query.rstrip(", ") + " WHERE id = ?"
        update_values.append(book_id)
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(update_query, tuple(update_values))

    def search(self, **info: Unpack[PartialQueriedBookInfo]) -> List[QueriedBookInfo]:
        verify_keys(info, PartialQueriedBookInfo, fullmatch=False)
        query = "SELECT * FROM books"
        params: List[Any] = []
        if info:
            query += " WHERE "
            conditions = []
            for key, value in info.items():
                conditions.append(f"{key} = ?")
                params.append(value)
            query += " AND ".join(conditions)
        with self._lock.read_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
        books = []
        for row in rows:
            book = QueriedBookInfo(  # type: ignore[misc]
                {
                    k: (
                        json.loads(row[i])
                        if QueriedBookInfo.__annotations__[k] == _JSONType
                        else row[i]
                    )
                    for i, k in enumerate(QueriedBookInfo.__annotations__.keys())
                }
            )
            books.append(book)
        return books

    def vacuum(self):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")


if __name__ == "__main__":
    db = BookDB("./books.db")
