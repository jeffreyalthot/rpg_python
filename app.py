from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Set

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_user, get_user_by_username, init_db, verify_password
from game_logic import MAX_ACTION_POINTS, RECHARGE_PER_HOUR, PlayerState, normalize_player_state

app = FastAPI(title="RPG Multiplayer PA")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

players: Dict[str, PlayerState] = {}
connections: Set[WebSocket] = set()


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


def get_or_create_player(username: str) -> PlayerState:
    if username not in players:
        players[username] = PlayerState(action_points=MAX_ACTION_POINTS, last_recharge_at=datetime.now(timezone.utc))
    return normalize_player_state(players[username])


async def broadcast_states() -> None:
    payload = {
        "type": "snapshot",
        "players": {
            name: {
                "action_points": normalize_player_state(state).action_points,
            }
            for name, state in players.items()
        },
    }
    disconnected: Set[WebSocket] = set()
    for ws in connections:
        try:
            await ws.send_json(payload)
        except Exception:
            disconnected.add(ws)

    for ws in disconnected:
        connections.discard(ws)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "max_pa": MAX_ACTION_POINTS})


@app.post("/api/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: str = Form(...),
):
    username = username.strip()
    email = email.strip()
    first_name = first_name.strip()
    last_name = last_name.strip()
    birth_date = birth_date.strip()

    if not username or not password:
        return JSONResponse({"error": "Username et mot de passe obligatoires"}, status_code=422)
    if len(password) < 6:
        return JSONResponse({"error": "Mot de passe trop court (6 min)"}, status_code=422)

    if not create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
    ):
        return JSONResponse({"error": "Ce username est déjà utilisé"}, status_code=409)

    return {"message": "Inscription réussie"}


@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    username = username.strip()
    if not username:
        return JSONResponse({"error": "Nom invalide"}, status_code=422)

    user = get_user_by_username(username)
    if user is None or not verify_password(password, user["password_hash"]):
        return JSONResponse({"error": "Identifiants invalides"}, status_code=401)

    state = get_or_create_player(username)
    await broadcast_states()
    return {
        "username": username,
        "action_points": state.action_points,
        "max_action_points": MAX_ACTION_POINTS,
        "recharge_per_hour": RECHARGE_PER_HOUR,
    }


@app.post("/api/action")
async def spend_action(username: str = Form(...)):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    state = normalize_player_state(players[username])
    if state.action_points <= 0:
        return JSONResponse({"error": "PA insuffisants"}, status_code=400)

    state.action_points -= 1
    players[username] = state
    await broadcast_states()

    return {
        "username": username,
        "action_points": state.action_points,
        "max_action_points": MAX_ACTION_POINTS,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    await broadcast_states()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)
