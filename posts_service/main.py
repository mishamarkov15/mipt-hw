import os
from datetime import datetime, timezone

import jwt
import psycopg
from fastapi import FastAPI, Header, Response, status
from pydantic import BaseModel


app = FastAPI(title="Posts service")

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")


class MessageIn(BaseModel):
    message: str


def connect():
    return psycopg.connect(DATABASE_URL)


def ensure_tables():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                time TIMESTAMPTZ NOT NULL,
                message TEXT NOT NULL
            )
            """
        )


@app.on_event("startup")
def on_startup():
    ensure_tables()


def get_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None

    token = authorization[len(prefix) :].strip()
    return token or None


@app.post("/messages", status_code=status.HTTP_201_CREATED)
def create_message(payload: MessageIn, authorization: str | None = Header(default=None)):
    token = get_bearer_token(authorization)
    if token is None:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    user_id = claims.get("user_id")
    if user_id is None:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, time, message) VALUES (%s, %s, %s)",
            (user_id, datetime.now(timezone.utc), payload.message),
        )

    return Response(status_code=status.HTTP_201_CREATED)
