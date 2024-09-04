from http.server import SimpleHTTPRequestHandler
from urllib import parse
import json
import functools

from . import database as db
from . import pages


def i_am_get_api(func):
    @functools.wraps(func)
    def wrapped(self: "ReqHandler", q: dict[str, list[str]]):
        if db.database is None:
            self.send_error(500, "Database Not Initialized")
            return
        params = {k: v(q[k][0]) for k, v in db.BOOKDB_CONTENT_DEF.items() if k in q}
        if "id" in q:
            params["id"] = int(q["id"][0])
        return func(self, params)

    return wrapped
# TODO: 重构一下让他们素质高点


class ReqHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = parse.urlparse(self.path)
        path = parsed_url.path
        query_params = parse.parse_qs(parsed_url.query)

        if path == "/":
            self.handle_root()
        elif path == "/search":
            self.search_api(query_params)
        elif path == "/add":
            self.add_api(query_params)
            # TODO: 改成 post
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        if self.path == "/delete":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            post_params = parse.parse_qs(post_data)
            # TODO: 写这个
        elif self.path == "/add":
            # TODO: 把 add 移过来
            pass
        else:
            self.send_error(404, "File Not Found")

    @i_am_get_api
    def search_api(self, params: dict[str, str]):
        result = db.database.search(**params)
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    @i_am_get_api
    def add_api(self, params: dict[str, str]):
        try:
            result = db.database.add(params)
        except db.KeysValidationFailure:
            self.send_error(400, "Wrong Request Params")
            return
        if result is None:
            self.send_error(500, "Unexpected Response from Database")
            return
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"id": result}, ensure_ascii=False).encode("utf-8"))

    @i_am_get_api
    def delete_api(self, params: dict[str, str]):
        # TODO: 写这个
        pass

    def handle_root(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(pages.ROOT_PAGE.encode("utf-8"))
