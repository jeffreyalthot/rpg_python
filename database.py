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
                hair TEXT NOT NULL DEFAULT 'Court',
                eyes TEXT NOT NULL DEFAULT 'Marron',
                mouth TEXT NOT NULL DEFAULT 'Neutre',
                nose TEXT NOT NULL DEFAULT 'Droit',
                ears TEXT NOT NULL DEFAULT 'Rondes',
                skin_tone TEXT NOT NULL DEFAULT 'Clair',
                starting_village TEXT NOT NULL DEFAULT 'Village départ 1',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        defaults = {
            "hair": "Court",
            "eyes": "Marron",
            "mouth": "Neutre",
            "nose": "Droit",
            "ears": "Rondes",
            "skin_tone": "Clair",
            "starting_village": "Village départ 1",
        }
        for col, default_value in defaults.items():
            if col not in existing_columns:
                safe_default = default_value.replace("'", "''")
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT '{safe_default}'")


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
    hair: str,
    eyes: str,
    mouth: str,
    nose: str,
    ears: str,
    skin_tone: str,
    starting_village: str,
) -> bool:
    payload = {
        "username": username,
        "password_hash": hash_password(password),
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": birth_date,
        "hair": hair,
        "eyes": eyes,
        "mouth": mouth,
        "nose": nose,
        "ears": ears,
        "skin_tone": skin_tone,
        "starting_village": starting_village,
    }
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username, password_hash, email, first_name, last_name, birth_date,
                    hair, eyes, mouth, nose, ears, skin_tone, starting_village
                )
                VALUES (
                    :username, :password_hash, :email, :first_name, :last_name, :birth_date,
                    :hair, :eyes, :mouth, :nose, :ears, :skin_tone, :starting_village
                )
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
