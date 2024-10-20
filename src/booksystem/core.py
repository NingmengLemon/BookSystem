import logging
import time
from typing import Annotated
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException, Depends, Cookie, Query, Body, Response
from sqlmodel import col, create_engine, SQLModel, Session, select
from passlib.hash import argon2
from apscheduler.schedulers.background import BackgroundScheduler

from .models import User, Book, LoginSession
from .models import (
    UserInfoResp,
    LoginPayload,
    BookAddPayload,
    RegisterPayload,
    BookQueryPayload,
    BookModifyPayload,
)

LOGIN_SESSION_EXPIRES = 60 * 60 * 24

app = FastAPI()
logger = logging.getLogger(__name__)

db_filename = "booksys.db"
db_url = f"sqlite:///{db_filename}"

db_engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(db_engine)


def get_dbsession():
    with Session(db_engine) as session:
        yield session


DbSessDep = Annotated[Session, Depends(get_dbsession)]


def clear_expired_session():
    with Session(db_engine) as dbsession:
        sesss = dbsession.exec(
            select(LoginSession).where(LoginSession.expire_at <= time.time())
        ).all()
        if sesss:
            for s in sesss:
                dbsession.delete(s)
            dbsession.commit()
            logger.info("cleared %d expired sessions", len(sesss))


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    scheduler = BackgroundScheduler()
    scheduler.add_job(clear_expired_session, "interval", minutes=LOGIN_SESSION_EXPIRES)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/teapot")
async def teapot():
    raise HTTPException(status_code=418)


@app.post("/api/register")
async def register(payload: RegisterPayload, dbsession: DbSessDep):
    if dbsession.exec(select(User).where(User.username == payload.username)).all():
        raise HTTPException(status_code=409, detail="User already exists")
    user = User.model_validate(
        payload, update={"password": argon2.hash(payload.password)}
    )
    dbsession.add(user)
    dbsession.commit()
    return {"user_id": user.id}


async def verify_session(
    dbsession: DbSessDep, session_id: uuid.UUID | None = Cookie(None)
):
    if session_id:
        if sess := dbsession.exec(
            select(LoginSession).where(LoginSession.id == session_id)
        ).one_or_none():
            if sess.expire_at > time.time():
                return sess
            dbsession.delete(sess)
            dbsession.commit()
    raise HTTPException(status_code=401, detail="Session invalid or expired")


LoginSessDep = Annotated[LoginSession, Depends(verify_session)]


@app.post("/api/login")
async def login(payload: LoginPayload, dbsession: DbSessDep, response: Response):
    if user := dbsession.exec(
        select(User).where(User.username == payload.username)
    ).one_or_none():
        if argon2.verify(payload.password, user.password):
            expires = time.time() + LOGIN_SESSION_EXPIRES
            login_session = LoginSession(user_id=user.id, expire_at=expires)
            dbsession.add(login_session)
            dbsession.commit()
            response.set_cookie(
                "session_id", login_session.id, expires=int(expires), httponly=True
            )
            return {"session_id": login_session.id}
    raise HTTPException(status_code=401, detail="Wrong password or user does not exist")


@app.post("/api/logout")
async def logout(
    dbsession: DbSessDep,
    response: Response,
    login_session: LoginSessDep,
):
    response.delete_cookie("session_id")
    dbsession.delete(login_session)
    dbsession.commit()
    return "ok"


@app.post("/api/me")
async def me(
    dbsession: DbSessDep,
    login_session: LoginSessDep,
):
    user = dbsession.exec(select(User).where(User.id == login_session.user_id)).one()
    return UserInfoResp.model_validate(user).model_dump()


@app.post("/api/book/add")
async def add_book(
    payload: BookAddPayload,
    dbsession: DbSessDep,
    login_session: LoginSessDep,
):
    book = Book.model_validate(payload, update={"owner_id": login_session.user_id})
    dbsession.add(book)
    dbsession.commit()
    return {"book_id": book.id}


@app.post("/api/book/query")
async def query_book(
    dbsession: DbSessDep,
    login_session: LoginSessDep,
    payload: BookQueryPayload = Body(None),
    page_size: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    if not payload:
        payload = BookQueryPayload()
    constrs = [
        col(vars(Book)[key]).icontains(value)
        for key, value in payload.model_dump().items()
        if value is not None
    ]
    return dbsession.exec(
        select(Book)
        .where(Book.owner_id == login_session.user_id, *constrs)
        .offset(offset)
        .limit(page_size)
        .order_by(Book.name)
    ).all()


@app.post("/api/book/modify")
async def modify_book(
    payload: BookModifyPayload,
    dbsession: DbSessDep,
    login_session: LoginSessDep,
):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    book_id = changes.pop("id")
    book = dbsession.exec(
        select(Book).where(
            Book.id == book_id,
            Book.owner_id == login_session.user_id,
        )
    ).one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    for k, v in changes.items():
        setattr(book, k, v)
    dbsession.add(book)
    dbsession.commit()
    dbsession.refresh(book)
    return {"book_id": book.id}


@app.post("/api/book/delete")
async def delete_book(
    book_ids: list[uuid.UUID] | uuid.UUID,
    dbsession: DbSessDep,
    login_session: LoginSessDep,
):
    if isinstance(book_ids, uuid.UUID):
        book_ids = [book_ids]
    succ = []
    fail = []
    for i in book_ids:
        book = dbsession.exec(
            select(Book).where(
                Book.id == i,
                Book.owner_id == login_session.user_id,
            )
        ).one_or_none()
        if not book:
            fail.append(i)
            continue
        dbsession.delete(book)
        succ.append(i)
    if succ:
        dbsession.commit()
    return {
        "succ": succ,
        "fail": fail,
    }
