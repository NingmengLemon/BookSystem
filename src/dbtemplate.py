import sqlite3
from typing import TypeAlias, List, Any, Type, Mapping

from rwlock import ReadWriteLock

_TYPE_TO_SQLITE_TYPE_MAP = {
    str: "TEXT",
    int: "INTEGER",
    float: "REAL",
    None: "NULL",
    type(None): "NULL",
    bytes: "BLOB",
}


def type_to_sqlitetype(t: Type) -> str | None:
    """将类型转换为 SQLite 中的类型

    :param t: 要被转换的类型
    :type t: Type
    :return: SQLite 类型，`None` 表示失败
    :rtype: str | None
    """
    return _TYPE_TO_SQLITE_TYPE_MAP.get(t)


DBContentDef: TypeAlias = Mapping[str, Any]


def dbcls_factory(datadef: DBContentDef, cls_name: str, table_name: str | None = None):
    """从 `datadef` 动态生成一个继承自 `_DataBase` 的数据库类定义

    :param datadef: 数据库类定义中的表字段定义
    :type datadef: DBContentDef
    :param cls_name: 类定义的名称
    :type cls_name: str
    :param table_name: 表的名称，省略时取 `cls_name` 的值
    :type table_name: str | None, optional
    :return: 新建的数据库类定义
    :rtype: Type[_DataBase]
    """
    if table_name is None:
        table_name = cls_name

    def init(self, dbpath: str):
        _DataBase.__init__(self, dbpath, datadef, table_name)

    return type(cls_name, (_DataBase,), {"__init__": init})


class KeysValidationFailure(Exception):
    """当键验证不通过时抛出此错误"""


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

    @staticmethod
    def _validate_keys(d: Mapping, dt: DBContentDef, fullmatch=False):
        """以 `dt` 为标准验证 `d` 中的键

        :param d: 被验证的映射
        :type d: Mapping
        :param dt: 作为标准的映射
        :type dt: DBContentDef
        :param fullmatch: 是否必须全部匹配, defaults to False
        :type fullmatch: bool, optional
        :raises KeysValidationFailure:
        """
        dt_keys = set(dt.keys())
        d_keys = set(d.keys())

        if fullmatch:
            if d_keys != dt_keys:
                raise KeysValidationFailure("keys not equal")
            return

        unexpected_keys = d_keys - dt_keys
        if unexpected_keys:
            raise KeysValidationFailure(
                f"unexpected keys: {', '.join(unexpected_keys)}"
            )

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

    def add(self, item: dict[str, Any]) -> int | None:
        """增加条目

        :param item: 要增加的条目，键必须与定义完全相同（不计顺序）
        :type item: dict[str, Any]
        :return: 新增的条目在数据库中的id
        :rtype: int | None
        """           
        self._validate_keys(item, self._datadef, fullmatch=True)
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
                [item[k] for k in self._datadef.keys()],
            )
            return cursor.lastrowid

    def delete(self, item_id: int):
        """删除条目

        :param item_id: 要删除的条目在数据库中的唯一id
        :type item_id: int
        """
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self._table_name} WHERE id = ?", (item_id,))

    def modify(self, item_id: int, **info):
        """修改条目

        :param item_id: 要修改的条目在数据库中的唯一id
        :type item_id: int
        """
        if not info:
            return
        self._validate_keys(info, self._datadef, fullmatch=False)
        update_query = f"UPDATE {self._table_name} SET "
        update_values = []
        for key, value in info.items():
            update_query += f"{key} = ?, "
            update_values.append(value)
        update_query = update_query.rstrip(", ") + " WHERE id = ?"
        update_values.append(item_id)
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(update_query, tuple(update_values))

    def search(self, **info) -> List[dict]:
        """查找条目

        :return: 找到的条目们
        :rtype: List[dict]
        """
        self._validate_keys(info, self._datadef_with_id, fullmatch=False)
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
            book = {k: row[i] for i, k in enumerate(self._datadef_with_id.keys())}
            books.append(book)
        return books

    def vacuum(self):
        with self._lock.write_lock(), self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")


if __name__ == "__main__":
    BOOKDB_CONTENT_DEF = {
        "title": str,
        "isbn": str,  # ISBN 13
        "author": str,
        "publisher": str,
        "desc": str,
        "cover": str,
        "price": float,
        "extra": str,
    }
    BookDB = dbcls_factory(BOOKDB_CONTENT_DEF, "BookDB", "books")
    db = BookDB("./books.db")
