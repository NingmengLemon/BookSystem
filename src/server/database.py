from dbtemplate import dbcls_factory, KeysValidationFailure

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

database = None


def init(dbpath="./books.db"):
    global database
    if database is None:
        database = BookDB(dbpath)
