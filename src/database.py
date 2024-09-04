import sqlite3
import json
from typing import (
    TypeAlias,
    Union,
    List,
    Dict,
    Any,
    Type,
    Mapping,
)

from rwlock import ReadWriteLock


_JSONType: TypeAlias = Union[
    str, int, float, bool, None, Dict[str, "_JSONType"], List["_JSONType"]
]


BOOKDB_CONTENT_DEF = {
    "title": str,
    "isbn": str,  # ISBN 13
    "author": str,
    "publisher": str,
    "desc": str,
    "cover": str,
    "price": float,
    "extra": _JSONType,
}

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


DBContentDef: TypeAlias = Mapping[str, Any]


def verify_keys(d: Mapping, dt: DBContentDef, fullmatch=False):
    anno = dt
    if fullmatch:
        assert set(d.keys()) == set(anno.keys()), "keys not equal"
    for k in d.keys():
        assert k in anno, f"unexpected key: {k}"


def dbcls_factory(datadef: DBContentDef, cls_name: str, table_name: str):
    def init(self, dbpath: str):
        _DataBase.__init__(self, dbpath, datadef, table_name)

    return type(cls_name, (_DataBase,), {"__init__": init})


class _DataBase:
    def __init__(
        self, dbpath: str, datadef: DBContentDef, tablename: str = "database"
    ) -> None:
        self._datadef = dict(datadef)
        self._datadef_with_id = dict(datadef)
        self._datadef_with_id["id"] = int
        self._table_name = tablename

        self._dbpath = dbpath
        self._lock = ReadWriteLock()
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self._dbpath)

    def _create_table(self):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS {} (
                    {},
                    id INTEGER PRIMARY KEY AUTOINCREMENT
                )
                """.format(
                    self._table_name,
                    ", ".join(
                        [
                            f"{k} {type_to_sqlitetype(v)} NOT NULL"
                            for k, v in self._datadef.items()
                        ]
                    ),
                )
            )

    def add(self, book: dict):
        verify_keys(book, self._datadef, fullmatch=True)
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO {} ({})
                VALUES ({})
                """.format(
                    self._table_name,
                    ", ".join(self._datadef.keys()),
                    ", ".join(["?"] * len(self._datadef)),
                ),
                [
                    (json.dumps(book[k]) if v == _JSONType else book[k])  # type: ignore[literal-required]
                    for k, v in self._datadef.items()
                ],
            )

    def delete(self, item_id: int):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self._table_name} WHERE id = ?", (item_id,))

    def modify(self, item_id: int, **info):
        if not info:
            return
        verify_keys(info, self._datadef, fullmatch=False)
        update_query = f"UPDATE {self._table_name} SET "
        update_values = []
        for key, value in info.items():
            update_query += f"{key} = ?, "
            update_values.append(
                (json.dumps(value) if self._datadef[key] == _JSONType else value)
            )
        update_query = update_query.rstrip(", ") + " WHERE id = ?"
        update_values.append(item_id)
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(update_query, tuple(update_values))

    def search(self, **info) -> List[dict]:
        verify_keys(info, self._datadef_with_id, fullmatch=False)
        query = f"SELECT * FROM {self._table_name}"
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
            book = {
                k: (
                    json.loads(row[i])
                    if self._datadef_with_id[k] == _JSONType
                    else row[i]
                )
                for i, k in enumerate(self._datadef_with_id.keys())
            }
            books.append(book)
        return books

    def vacuum(self):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")


BookDB = dbcls_factory(BOOKDB_CONTENT_DEF, "BookDB", "books")


if __name__ == "__main__":
    db = BookDB("./books.db")
