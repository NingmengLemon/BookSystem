from http.server import HTTPServer
from socketserver import ThreadingMixIn
import socket

import stdlib_server

stdlib_server.init()


def find_free_port(starting_port):
    port = starting_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("localhost", port))
            if result != 0:  # If port is free
                return port
            port += 1


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


if __name__ == "__main__":
    server_address = ("", find_free_port(8080))
    httpd = ThreadingSimpleServer(server_address, stdlib_server.ReqHandler)

    print(f"Server running on port {server_address[1]}...")
    httpd.serve_forever()
