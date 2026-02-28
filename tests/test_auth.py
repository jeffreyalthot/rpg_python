import asyncio
from pathlib import Path

import app
import database


def test_register_and_login(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", Path(db_file))
    database.init_db()

    register_response = asyncio.run(
        app.register(
            username="hero",
            password="secret123",
            email="hero@example.com",
            first_name="Jean",
            last_name="Dupont",
            birth_date="1990-05-20",
        )
    )
    assert register_response["message"] == "Inscription réussie"

    duplicate_response = asyncio.run(
        app.register(
            username="hero",
            password="secret123",
            email="hero2@example.com",
            first_name="Paul",
            last_name="Durand",
            birth_date="1992-06-21",
        )
    )
    assert duplicate_response.status_code == 409

    login_response = asyncio.run(app.login(username="hero", password="secret123"))
    assert login_response["username"] == "hero"

    bad_login_response = asyncio.run(app.login(username="hero", password="bad"))
    assert bad_login_response.status_code == 401
