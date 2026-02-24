from pathlib import Path

from fastapi.testclient import TestClient

import app
import database


def test_register_and_login(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", Path(db_file))
    database.init_db()

    client = TestClient(app.app)

    register_response = client.post(
        "/api/register",
        data={
            "username": "hero",
            "password": "secret123",
            "email": "hero@example.com",
            "first_name": "Jean",
            "last_name": "Dupont",
            "birth_date": "1990-05-20",
        },
    )
    assert register_response.status_code == 200

    duplicate_response = client.post(
        "/api/register",
        data={
            "username": "hero",
            "password": "secret123",
            "email": "hero2@example.com",
            "first_name": "Paul",
            "last_name": "Durand",
            "birth_date": "1992-06-21",
        },
    )
    assert duplicate_response.status_code == 409

    login_response = client.post("/api/login", data={"username": "hero", "password": "secret123"})
    assert login_response.status_code == 200
    assert login_response.json()["username"] == "hero"

    bad_login_response = client.post("/api/login", data={"username": "hero", "password": "bad"})
    assert bad_login_response.status_code == 401
