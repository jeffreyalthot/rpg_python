import base64
import hashlib
import json
import os
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

DB_PATH = "game.db"
HOST = "0.0.0.0"
PORT = 5050
MAX_ACTION_POINTS = 20
REGEN_PER_HOUR = 2
ACTION_COST = 5


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    action_points INTEGER NOT NULL DEFAULT 20,
                    last_regen INTEGER NOT NULL,
                    avatar BLOB
                )
                """
            )
            conn.commit()

    def _regen_action_points(self, row: sqlite3.Row) -> int:
        now = int(time.time())
        current_ap = int(row["action_points"])
        last_regen = int(row["last_regen"])
        elapsed_hours = (now - last_regen) // 3600

        if elapsed_hours <= 0:
            return current_ap

        gained = elapsed_hours * REGEN_PER_HOUR
        new_ap = min(MAX_ACTION_POINTS, current_ap + gained)

        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET action_points = ?, last_regen = ? WHERE id = ?",
                (new_ap, now, row["id"]),
            )
            conn.commit()
        return new_ap

    def register(self, username: str, password: str) -> tuple[bool, str]:
        salt = os.urandom(16).hex()
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
        ).hex()
        now = int(time.time())

        with self.lock:
            try:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO users (username, password_hash, salt, action_points, last_regen)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (username, password_hash, salt, MAX_ACTION_POINTS, now),
                    )
                    conn.commit()
            except sqlite3.IntegrityError:
                return False, "Nom d'utilisateur déjà pris."
        return True, "Compte créé avec succès."

    def login(self, username: str, password: str) -> tuple[bool, str, Optional[dict]]:
        with self.lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()

        if not row:
            return False, "Utilisateur introuvable.", None

        test_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(row["salt"]),
            120_000,
        ).hex()

        if test_hash != row["password_hash"]:
            return False, "Mot de passe invalide.", None

        ap = self._regen_action_points(row)
        user_data = {
            "username": row["username"],
            "action_points": ap,
            "max_action_points": MAX_ACTION_POINTS,
        }
        return True, "Connexion réussie.", user_data

    def get_user_state(self, username: str) -> Optional[dict]:
        with self.lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()
        if not row:
            return None
        ap = self._regen_action_points(row)
        return {
            "username": row["username"],
            "action_points": ap,
            "max_action_points": MAX_ACTION_POINTS,
        }

    def consume_action_points(self, username: str, amount: int) -> tuple[bool, str, Optional[int]]:
        with self.lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()
                if not row:
                    return False, "Utilisateur introuvable.", None

                current = self._regen_action_points(row)
                if current < amount:
                    return False, "PA insuffisants.", current

                new_ap = current - amount
                conn.execute(
                    "UPDATE users SET action_points = ?, last_regen = ? WHERE username = ?",
                    (new_ap, int(time.time()), username),
                )
                conn.commit()
                return True, "Action effectuée.", new_ap

    def save_avatar(self, username: str, image_b64: str) -> tuple[bool, str]:
        try:
            blob = base64.b64decode(image_b64)
        except Exception:
            return False, "Image invalide (base64)."

        with self.lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET avatar = ? WHERE username = ?", (blob, username)
                )
                conn.commit()
        return True, "Avatar enregistré."

    def load_avatar(self, username: str) -> Optional[str]:
        with self.lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT avatar FROM users WHERE username = ?", (username,)
                ).fetchone()
        if not row or row["avatar"] is None:
            return None
        return base64.b64encode(row["avatar"]).decode("ascii")


@dataclass
class ClientSession:
    sock: socket.socket
    addr: tuple
    username: Optional[str] = None


class GameServer:
    def __init__(self, host: str, port: int, db: Database):
        self.host = host
        self.port = port
        self.db = db
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sessions: Dict[socket.socket, ClientSession] = {}
        self.sessions_lock = threading.Lock()

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        print(f"[SERVER] En écoute sur {self.host}:{self.port}")

        while True:
            client_sock, addr = self.server_socket.accept()
            session = ClientSession(sock=client_sock, addr=addr)
            with self.sessions_lock:
                self.sessions[client_sock] = session
            print(f"[SERVER] Connexion de {addr}")
            threading.Thread(target=self._handle_client, args=(session,), daemon=True).start()

    def _send(self, session: ClientSession, payload: dict):
        try:
            message = json.dumps(payload, ensure_ascii=False) + "\n"
            session.sock.sendall(message.encode("utf-8"))
        except OSError:
            self._disconnect(session)

    def _broadcast(self, payload: dict, exclude: Optional[socket.socket] = None):
        with self.sessions_lock:
            sessions = list(self.sessions.values())
        for sess in sessions:
            if exclude and sess.sock == exclude:
                continue
            if sess.username:
                self._send(sess, payload)

    def _online_users(self):
        with self.sessions_lock:
            return [s.username for s in self.sessions.values() if s.username]

    def _disconnect(self, session: ClientSession):
        username = session.username
        with self.sessions_lock:
            if session.sock in self.sessions:
                del self.sessions[session.sock]
        try:
            session.sock.close()
        except OSError:
            pass

        if username:
            self._broadcast({"type": "players", "players": self._online_users()})
            self._broadcast(
                {"type": "chat", "from": "Serveur", "message": f"{username} s'est déconnecté."}
            )

    def _handle_client(self, session: ClientSession):
        buffer = ""
        try:
            while True:
                chunk = session.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._handle_message(session, line)
        except OSError:
            pass
        finally:
            self._disconnect(session)

    def _handle_message(self, session: ClientSession, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            self._send(session, {"type": "error", "message": "JSON invalide."})
            return

        action = msg.get("action")

        if action == "register":
            username = msg.get("username", "").strip()
            password = msg.get("password", "")
            if not username or not password:
                self._send(session, {"type": "register", "ok": False, "message": "Champs requis."})
                return
            ok, message = self.db.register(username, password)
            self._send(session, {"type": "register", "ok": ok, "message": message})
            return

        if action == "login":
            username = msg.get("username", "").strip()
            password = msg.get("password", "")
            ok, message, user_data = self.db.login(username, password)
            if not ok:
                self._send(session, {"type": "login", "ok": False, "message": message})
                return

            session.username = username
            self._send(session, {"type": "login", "ok": True, "message": message, "user": user_data})
            self._broadcast({"type": "players", "players": self._online_users()})
            self._broadcast({"type": "chat", "from": "Serveur", "message": f"{username} a rejoint la partie."})
            return

        if not session.username:
            self._send(session, {"type": "error", "message": "Connectez-vous d'abord."})
            return

        if action == "get_state":
            state = self.db.get_user_state(session.username)
            if state:
                self._send(session, {"type": "state", "user": state, "players": self._online_users()})
            return

        if action == "play_action":
            ok, message, new_ap = self.db.consume_action_points(session.username, ACTION_COST)
            self._send(
                session,
                {
                    "type": "play_action",
                    "ok": ok,
                    "message": message,
                    "action_cost": ACTION_COST,
                    "action_points": new_ap,
                },
            )
            if ok:
                self._broadcast(
                    {
                        "type": "chat",
                        "from": "Serveur",
                        "message": f"{session.username} a utilisé {ACTION_COST} PA.",
                    }
                )
            return

        if action == "chat":
            text = msg.get("message", "").strip()
            if text:
                self._broadcast({"type": "chat", "from": session.username, "message": text})
            return

        if action == "upload_avatar":
            data = msg.get("image_b64", "")
            ok, message = self.db.save_avatar(session.username, data)
            self._send(session, {"type": "upload_avatar", "ok": ok, "message": message})
            return

        if action == "get_avatar":
            image_b64 = self.db.load_avatar(session.username)
            self._send(session, {"type": "avatar", "image_b64": image_b64})
            return

        self._send(session, {"type": "error", "message": f"Action inconnue: {action}"})


if __name__ == "__main__":
    db = Database(DB_PATH)
    server = GameServer(HOST, PORT, db)
    server.start()
