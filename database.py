from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path("rpg.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return hmac.compare_digest(digest.hex(), expected)


def create_user(
    *,
    username: str,
    password: str,
    email: str,
    first_name: str,
    last_name: str,
    birth_date: str,
) -> bool:
    payload = {
        "username": username,
        "password_hash": hash_password(password),
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": birth_date,
    }
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, email, first_name, last_name, birth_date)
                VALUES (:username, :password_hash, :email, :first_name, :last_name, :birth_date)
                """,
                payload,
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cur.fetchone()
