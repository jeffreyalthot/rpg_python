from __future__ import annotations

from datetime import datetime, timezone
from collections import deque
from random import Random
from typing import Deque, Dict, Set

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_user, get_user_by_username, init_db, verify_password
from game_logic import MAX_ACTION_POINTS, RECHARGE_PER_HOUR, PlayerState, normalize_player_state
from game_progress import HeroProfile, apply_adventure, hero_snapshot, outcome_for_tile
from world_map import build_world, world_snapshot

app = FastAPI(title="RPG Multiplayer PA")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

players: Dict[str, PlayerState] = {}
heroes: Dict[str, HeroProfile] = {}
player_guilds: Dict[str, str] = {}
guild_members: Dict[str, Set[str]] = {}
guild_messages: Dict[str, Deque[dict]] = {}
connections: Set[WebSocket] = set()
world = build_world()
MAX_GUILD_MESSAGES = 25
raid_boss_names = ["Hydre Astrale", "Titan de Cendre", "Liche du Néant", "Golem Tempête"]
raid_state = {
    "name": raid_boss_names[0],
    "level": 1,
    "max_hp": 600,
    "hp": 600,
    "guild_damage": {},
    "last_reset_at": datetime.now(timezone.utc).isoformat(),
}


def raid_snapshot() -> dict:
    ranking = [
        {"guild": guild, "damage": damage}
        for guild, damage in sorted(raid_state["guild_damage"].items(), key=lambda item: (-item[1], item[0].lower()))
    ]
    return {
        "name": raid_state["name"],
        "level": raid_state["level"],
        "max_hp": raid_state["max_hp"],
        "hp": raid_state["hp"],
        "ranking": ranking,
        "last_reset_at": raid_state["last_reset_at"],
    }


def reset_raid(next_level: int) -> None:
    raid_state["level"] = next_level
    raid_state["max_hp"] = 600 + (next_level - 1) * 140
    raid_state["hp"] = raid_state["max_hp"]
    raid_state["name"] = raid_boss_names[(next_level - 1) % len(raid_boss_names)]
    raid_state["guild_damage"] = {}
    raid_state["last_reset_at"] = datetime.now(timezone.utc).isoformat()


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


def get_or_create_player(username: str) -> PlayerState:
    if username not in players:
        players[username] = PlayerState(action_points=MAX_ACTION_POINTS, last_recharge_at=datetime.now(timezone.utc))
    return normalize_player_state(players[username])


def get_or_create_hero(username: str) -> HeroProfile:
    if username not in heroes:
        heroes[username] = HeroProfile()
    return heroes[username]


async def broadcast_states() -> None:
    guild_snapshot = [
        {
            "name": name,
            "member_count": len(members),
        }
        for name, members in sorted(guild_members.items(), key=lambda item: (-len(item[1]), item[0].lower()))
    ]

    payload = {
        "type": "snapshot",
        "players": {
            name: {
                "action_points": normalize_player_state(state).action_points,
            }
            for name, state in players.items()
        },
        "guilds": guild_snapshot,
        "raid": raid_snapshot(),
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
    hero = get_or_create_hero(username)
    await broadcast_states()
    guild_name = player_guilds.get(username)
    guild_chat = list(guild_messages[guild_name]) if guild_name in guild_messages else []

    return {
        "username": username,
        "action_points": state.action_points,
        "max_action_points": MAX_ACTION_POINTS,
        "recharge_per_hour": RECHARGE_PER_HOUR,
        "hero": hero_snapshot(hero),
        "guild": guild_name,
        "guild_chat": guild_chat,
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


@app.post("/api/adventure")
async def adventure(username: str = Form(...), tile_kind: str = Form("plain")):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    state = normalize_player_state(players[username])
    if state.action_points <= 0:
        return JSONResponse({"error": "PA insuffisants"}, status_code=400)

    state.action_points -= 1
    players[username] = state

    hero = get_or_create_hero(username)
    rng = Random(f"{username}:{datetime.now(timezone.utc).isoformat()}")
    outcome = outcome_for_tile(tile_kind.strip(), rng)
    details = apply_adventure(hero, outcome)

    await broadcast_states()

    return {
        "username": username,
        "action_points": state.action_points,
        "max_action_points": MAX_ACTION_POINTS,
        "hero": hero_snapshot(hero),
        "outcome": details,
    }




@app.get("/api/world")
async def get_world():
    return world_snapshot(world)


@app.get("/api/guilds")
async def get_guilds():
    ranking = [
        {"name": name, "member_count": len(members)}
        for name, members in sorted(guild_members.items(), key=lambda item: (-len(item[1]), item[0].lower()))
    ]
    return {"guilds": ranking}


@app.get("/api/raids/current")
async def get_current_raid():
    return raid_snapshot()


@app.post("/api/raids/attack")
async def attack_raid_boss(username: str = Form(...)):
    username = username.strip()
    guild_name = player_guilds.get(username)

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if guild_name is None or guild_name not in guild_members:
        return JSONResponse({"error": "Rejoignez une guilde pour attaquer le boss de raid"}, status_code=409)

    state = normalize_player_state(players[username])
    if state.action_points <= 0:
        return JSONResponse({"error": "PA insuffisants"}, status_code=400)

    state.action_points -= 1
    players[username] = state

    hero = get_or_create_hero(username)
    rng = Random(f"raid:{username}:{datetime.now(timezone.utc).isoformat()}")
    damage = 8 + hero.level * 2 + rng.randint(0, 6)
    raid_state["hp"] = max(0, raid_state["hp"] - damage)
    raid_state["guild_damage"][guild_name] = raid_state["guild_damage"].get(guild_name, 0) + damage

    defeated = raid_state["hp"] <= 0
    defeated_boss = None
    if defeated:
        defeated_boss = {
            "name": raid_state["name"],
            "level": raid_state["level"],
        }
        reset_raid(raid_state["level"] + 1)

    await broadcast_states()

    return {
        "damage": damage,
        "action_points": state.action_points,
        "defeated": defeated,
        "defeated_boss": defeated_boss,
        "raid": raid_snapshot(),
    }


@app.post("/api/guilds/create")
async def create_guild(username: str = Form(...), guild_name: str = Form(...)):
    username = username.strip()
    guild_name = guild_name.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if len(guild_name) < 3:
        return JSONResponse({"error": "Le nom de guilde doit contenir au moins 3 caractères"}, status_code=422)
    if guild_name in guild_members:
        return JSONResponse({"error": "Cette guilde existe déjà"}, status_code=409)
    if username in player_guilds:
        return JSONResponse({"error": "Quittez votre guilde actuelle avant d'en créer une"}, status_code=409)

    guild_members[guild_name] = {username}
    player_guilds[username] = guild_name
    guild_messages[guild_name] = deque(
        [
            {
                "author": "Système",
                "message": f"{username} a fondé la guilde {guild_name}.",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        maxlen=MAX_GUILD_MESSAGES,
    )
    await broadcast_states()

    return {
        "guild": guild_name,
        "member_count": 1,
        "chat": list(guild_messages[guild_name]),
    }


@app.post("/api/guilds/join")
async def join_guild(username: str = Form(...), guild_name: str = Form(...)):
    username = username.strip()
    guild_name = guild_name.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if guild_name not in guild_members:
        return JSONResponse({"error": "Guilde introuvable"}, status_code=404)
    if username in player_guilds:
        return JSONResponse({"error": "Vous êtes déjà dans une guilde"}, status_code=409)

    guild_members[guild_name].add(username)
    player_guilds[username] = guild_name
    guild_messages.setdefault(guild_name, deque(maxlen=MAX_GUILD_MESSAGES)).append(
        {
            "author": "Système",
            "message": f"{username} rejoint la guilde.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await broadcast_states()

    return {
        "guild": guild_name,
        "member_count": len(guild_members[guild_name]),
        "chat": list(guild_messages[guild_name]),
    }


@app.post("/api/guilds/leave")
async def leave_guild(username: str = Form(...)):
    username = username.strip()
    guild_name = player_guilds.get(username)

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if guild_name is None:
        return JSONResponse({"error": "Vous n'appartenez à aucune guilde"}, status_code=409)

    members = guild_members[guild_name]
    members.discard(username)
    player_guilds.pop(username, None)

    if members:
        guild_messages.setdefault(guild_name, deque(maxlen=MAX_GUILD_MESSAGES)).append(
            {
                "author": "Système",
                "message": f"{username} quitte la guilde.",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        member_count = len(members)
        chat = list(guild_messages[guild_name])
    else:
        guild_members.pop(guild_name, None)
        guild_messages.pop(guild_name, None)
        member_count = 0
        chat = []

    await broadcast_states()
    return {
        "guild": None,
        "member_count": member_count,
        "chat": chat,
    }


@app.post("/api/guilds/chat")
async def post_guild_message(username: str = Form(...), message: str = Form(...)):
    username = username.strip()
    content = message.strip()
    guild_name = player_guilds.get(username)

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if guild_name is None or guild_name not in guild_members:
        return JSONResponse({"error": "Vous devez rejoindre une guilde"}, status_code=409)
    if len(content) < 2:
        return JSONResponse({"error": "Message trop court"}, status_code=422)

    guild_messages.setdefault(guild_name, deque(maxlen=MAX_GUILD_MESSAGES)).append(
        {
            "author": username,
            "message": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {
        "guild": guild_name,
        "chat": list(guild_messages[guild_name]),
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
