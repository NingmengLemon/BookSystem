from http.server import SimpleHTTPRequestHandler
from urllib import parse
import json
import functools
from typing import Any
import sqlite3
import logging
import os

from . import database as db


def i_am_post_api(func):
    @functools.wraps(func)
    def wrapped(self: "ReqHandler"):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length).decode("utf-8")
        try:
            json_data = json.loads(post_data)
            return func(self, json_data)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")

    return wrapped


@functools.singledispatch
def parse_delete_api_params(params: Any):
    return []


@parse_delete_api_params.register
def _(params: dict):
    return params.get("ids", [])


@parse_delete_api_params.register
def _(params: list):
    ids = []
    for p in params:
        if isinstance(p, int):
            ids.append(p)
        elif isinstance(p, dict):
            if "id" in p:
                ids.append(p["id"])
    return ids


@parse_delete_api_params.register
def _(params: int):
    return [params]


class ReqHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if db.database is None:
            self.send_error(500, "Database Not Initialized")
            return
        
        
        parsed_url = parse.urlparse(self.path)
        path = parsed_url.path
        query_params = parse.parse_qs(parsed_url.query)
        if self.path == "/":
            self.serve_html("static/index.html")
        elif path == "/search":
            self.search_api(query_params)
        else:
            self.send_error(404, "File Not Found")
            
    def serve_html(self, file_path):
        if os.path.exists(file_path):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        if db.database is None:
            self.send_error(500, "Database Not Initialized")
            return
        if self.path == "/delete":
            self.delete_api()
        elif self.path == "/add":
            self.add_api()
        else:
            self.send_error(404, "File Not Found")

    def search_api(self, q: dict[str, list[str]]):
        params = {k: v(q[k][0]) for k, v in db.BOOKDB_CONTENT_DEF.items() if k in q}
        if "id" in q:
            params["id"] = int(q["id"][0])
        result = db.database.search(**params)
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    @i_am_post_api
    def add_api(self, params: Any):
        if isinstance(params, dict):
            books = [params]
        elif isinstance(params, list):
            books = params
        else:
            self.send_error(400, "Wrong Request Params")
            return

        try:
            result = []
            for book in books:
                db.BookDB.validate_keys(book, db.BOOKDB_CONTENT_DEF, fullmatch=True)
            for book in books:
                result.append(db.database.add(book))
        except db.KeysValidationFailure:
            self.send_error(400, "Wrong Request Params")
            return
        except sqlite3.Error as e:
            logging.error("database error: %s", e)
            raise

        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            json.dumps({"ids": result}, ensure_ascii=False).encode("utf-8")
        )

    @i_am_post_api
    def delete_api(self, params):
        ids = parse_delete_api_params(params)
        succ = []
        for i in ids:
            try:
                db.database.delete(i)
            except sqlite3.Error as e:
                logging.error("Database Error: %s", e)
                raise
            else:
                succ.append(i)
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"ids": succ}, ensure_ascii=False).encode("utf-8"))

    @i_am_post_api
    def modify_api(self, params):
        pass