import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import psycopg
from fastapi import FastAPI, Response, status
from pydantic import BaseModel


app = FastAPI(title="Auth service")

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_TTL_MINUTES = int(os.environ.get("JWT_TTL_MINUTES", "60"))

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str
    password: str


def connect():
    return psycopg.connect(DATABASE_URL)


def ensure_tables():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            """
        )


@app.on_event("startup")
def on_startup():
    ensure_tables()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.fullmatch(email))


def is_safe_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(ch.islower() for ch in password)
        and any(ch.isupper() for ch in password)
        and any(ch.isdigit() for ch in password)
    )


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials):
    email = credentials.email.strip().lower()
    password = credentials.password

    if not is_valid_email(email) or not is_safe_password(password):
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s)",
                (email, password_hash),
            )
    except psycopg.errors.UniqueViolation:
        return Response(status_code=status.HTTP_409_CONFLICT)

    return Response(status_code=status.HTTP_201_CREATED)


@app.post("/login")
def login(credentials: Credentials):
    email = credentials.email.strip().lower()

    with connect() as conn:
        user = conn.execute(
            "SELECT id, password FROM users WHERE email = %s",
            (email,),
        ).fetchone()

    if user is None:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id, password_hash = user
    if not bcrypt.checkpw(credentials.password.encode("utf-8"), password_hash.encode("utf-8")):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MINUTES)
    token = jwt.encode(
        {"user_id": user_id, "exp": expires_at},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    return {"token": token}
