import sqlite3
import json
from typing import TypedDict, TypeAlias, Union, List, Dict, Unpack, Any

from rwlock import ReadWriteLock


JsonType: TypeAlias = Union[
    str, int, float, bool, None, Dict[str, "JsonType"], List["JsonType"]
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
    extra: JsonType


BookInfo: TypeAlias = _RequiredBookInfo


class PartialBookInfo(_RequiredBookInfo, total=False):
    pass


class QueriedBookInfo(_RequiredBookInfo, total=True):
    id: int


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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    isbn TEXT NOT NULL,
                    author TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    desc TEXT NOT NULL,
                    cover TEXT NOT NULL,
                    price REAL NOT NULL,
                    extra TEXT NOT NULL
                )
            """
            )

    def add(self, book: BookInfo):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO books (title, isbn, author, publisher, desc, cover, price, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    book["title"],
                    book["isbn"],
                    book["author"],
                    book["publisher"],
                    book["desc"],
                    book["cover"],
                    book["price"],
                    json.dumps(book["extra"]),
                ),
            )
            conn.commit()

    def delete(self, book_id: int):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()

    def modify(self, book_id: int, **info: Unpack[PartialBookInfo]):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            update_query = "UPDATE books SET "
            update_values = []
            for key, value in info.items():
                update_query += f"{key} = ?, "
                update_values.append(value)
            update_query = update_query.rstrip(", ")
            update_query += " WHERE id = ?"
            update_values.append(book_id)
            cursor.execute(update_query, tuple(update_values))
            conn.commit()

    def search(
        self, book_id: int | None = None, **info: Unpack[PartialBookInfo]
    ) -> List[QueriedBookInfo]:
        with self._lock.read_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM books"
            params: List[Any] = []
            if book_id is not None:
                query += " WHERE id = ?"
                params.append(book_id)
            elif info:
                query += " WHERE "
                conditions = []
                for key, value in info.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                query += " AND ".join(conditions)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            books = []
            for row in rows:
                book = QueriedBookInfo(
                    id=row[0],
                    title=row[1],
                    isbn=row[2],
                    author=row[3],
                    publisher=row[4],
                    desc=row[5],
                    cover=row[6],
                    price=row[7],
                    extra=json.loads(row[8]),
                )
                books.append(book)
            return books

    def vacuum(self):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
