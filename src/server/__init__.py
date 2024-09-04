from .server import ReqHandler
from . import database

def init():
    if database.database is None:
        database.init()