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
from game_content import CHARACTER_OPTIONS, ITEM_CATALOG
from game_logic import MAX_ACTION_POINTS, RECHARGE_PER_HOUR, PlayerState, normalize_player_state
from game_progress import HeroProfile, apply_adventure, hero_snapshot, outcome_for_tile, simulate_duel
from world_map import build_world, world_snapshot

app = FastAPI(title="RPG Multiplayer PA")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

players: Dict[str, PlayerState] = {}
heroes: Dict[str, HeroProfile] = {}
duel_stats: Dict[str, dict[str, int]] = {}
player_guilds: Dict[str, str] = {}
guild_members: Dict[str, Set[str]] = {}
guild_messages: Dict[str, Deque[dict]] = {}
global_messages: Deque[dict] = deque(
    [
        {
            "author": "Système",
            "message": "Bienvenue sur le canal mondial d'Aetheria.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ],
    maxlen=40,
)
party_board: Deque[dict] = deque(maxlen=60)
community_events: Deque[dict] = deque(
    [
        {
            "category": "system",
            "message": "Les chroniques communautaires sont actives.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ],
    maxlen=80,
)
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
contracts_pool = [
    {"title": "Reconstruire la Tour de Vigie", "description": "Livrez des matériaux pour restaurer la défense frontalière."},
    {"title": "Sécuriser la Route Marchande", "description": "Escortez les caravanes et éliminez les embuscades."},
    {"title": "Purger les Catacombes", "description": "Repoussez les créatures qui menacent les villages voisins."},
    {"title": "Rituel des Arcanes", "description": "Collectez des fragments mystiques pour les mages du royaume."},
]
contract_state = {
    "season": 1,
    "goal": 240,
    "progress": 0,
    "title": contracts_pool[0]["title"],
    "description": contracts_pool[0]["description"],
    "contributors": {},
    "last_rotation_at": datetime.now(timezone.utc).isoformat(),
}


def get_village_position(village_name: str) -> tuple[int, int]:
    for village in world.starting_villages:
        if village.name == village_name:
            return village.x, village.y
    default = world.starting_villages[0]
    return default.x, default.y


def profile_snapshot(user: dict) -> dict:
    return {
        "hair": user["hair"],
        "eyes": user["eyes"],
        "mouth": user["mouth"],
        "nose": user["nose"],
        "ears": user["ears"],
        "skin_tone": user["skin_tone"],
        "starting_village": user["starting_village"],
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


def get_or_create_duel_stats(username: str) -> dict[str, int]:
    if username not in duel_stats:
        duel_stats[username] = {"wins": 0, "losses": 0}
    return duel_stats[username]


def duel_leaderboard_snapshot() -> list[dict[str, int | str]]:
    ranking = sorted(
        (
            {
                "username": name,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total": stats["wins"] + stats["losses"],
            }
            for name, stats in duel_stats.items()
            if stats["wins"] + stats["losses"] > 0
        ),
        key=lambda entry: (-entry["wins"], entry["losses"], entry["username"].lower()),
    )
    return ranking[:10]


def contract_snapshot() -> dict:
    contributors = [
        {"username": name, "points": points}
        for name, points in sorted(contract_state["contributors"].items(), key=lambda item: (-item[1], item[0].lower()))
    ]
    return {
        "season": contract_state["season"],
        "goal": contract_state["goal"],
        "progress": contract_state["progress"],
        "title": contract_state["title"],
        "description": contract_state["description"],
        "contributors": contributors,
        "last_rotation_at": contract_state["last_rotation_at"],
    }


def party_board_snapshot() -> list[dict]:
    return list(party_board)


def community_events_snapshot() -> list[dict]:
    return list(community_events)


def push_community_event(category: str, message: str, actor: str | None = None) -> None:
    payload = {
        "category": category,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if actor:
        payload["actor"] = actor
    community_events.appendleft(payload)


def rotate_contracts() -> None:
    next_season = contract_state["season"] + 1
    template = contracts_pool[(next_season - 1) % len(contracts_pool)]
    contract_state["season"] = next_season
    contract_state["goal"] = 240 + (next_season - 1) * 40
    contract_state["progress"] = 0
    contract_state["title"] = template["title"]
    contract_state["description"] = template["description"]
    contract_state["contributors"] = {}
    contract_state["last_rotation_at"] = datetime.now(timezone.utc).isoformat()


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
        "contracts": contract_snapshot(),
        "duels": duel_leaderboard_snapshot(),
        "global_chat": list(global_messages),
        "party_board": party_board_snapshot(),
        "events": community_events_snapshot(),
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


@app.get("/play", response_class=HTMLResponse)
async def play(request: Request):
    return templates.TemplateResponse("play.html", {"request": request, "max_pa": MAX_ACTION_POINTS})


@app.get("/auth", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.get("/character", response_class=HTMLResponse)
async def character_page(request: Request):
    return templates.TemplateResponse("character.html", {"request": request})


@app.get("/world", response_class=HTMLResponse)
async def world_page(request: Request):
    return templates.TemplateResponse("world.html", {"request": request})


@app.get("/combat", response_class=HTMLResponse)
async def combat_page(request: Request):
    return templates.TemplateResponse("combat.html", {"request": request})


@app.get("/social", response_class=HTMLResponse)
async def social_page(request: Request):
    return templates.TemplateResponse("social.html", {"request": request})


@app.get("/game", response_class=HTMLResponse)
async def game_alias(request: Request):
    return templates.TemplateResponse("play.html", {"request": request, "max_pa": MAX_ACTION_POINTS})


@app.get("/api/options")
async def get_options():
    return {
        "character": CHARACTER_OPTIONS,
        "starting_villages": [v.__dict__ for v in world.starting_villages],
        "items": [{"name": name, **meta} for name, meta in ITEM_CATALOG.items()],
    }


@app.post("/api/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: str = Form(...),
    hair: str = Form(...),
    eyes: str = Form(...),
    mouth: str = Form(...),
    nose: str = Form(...),
    ears: str = Form(...),
    skin_tone: str = Form(...),
    starting_village: str = Form(...),
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

    if starting_village not in {v.name for v in world.starting_villages}:
        return JSONResponse({"error": "Village de départ invalide"}, status_code=422)

    char_payload = {
        "hair": hair,
        "eyes": eyes,
        "mouth": mouth,
        "nose": nose,
        "ears": ears,
        "skin_tone": skin_tone,
    }
    for field, value in char_payload.items():
        if value not in CHARACTER_OPTIONS[field]:
            return JSONResponse({"error": f"Option invalide pour {field}"}, status_code=422)

    if not create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        starting_village=starting_village,
        **char_payload,
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

    x, y = get_village_position(user["starting_village"])

    return {
        "username": username,
        "action_points": state.action_points,
        "max_action_points": MAX_ACTION_POINTS,
        "recharge_per_hour": RECHARGE_PER_HOUR,
        "hero": hero_snapshot(hero),
        "profile": profile_snapshot(user),
        "start_position": {"x": x, "y": y},
        "guild": guild_name,
        "guild_chat": guild_chat,
        "global_chat": list(global_messages),
        "duel_stats": get_or_create_duel_stats(username),
        "duel_leaderboard": duel_leaderboard_snapshot(),
        "party_board": party_board_snapshot(),
        "events": community_events_snapshot(),
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




@app.post("/api/combat/duel")
async def duel_player(username: str = Form(...), opponent: str = Form(...)):
    username = username.strip()
    opponent = opponent.strip()

    if username not in players or opponent not in players:
        return JSONResponse({"error": "Les deux joueurs doivent être connectés"}, status_code=404)
    if username == opponent:
        return JSONResponse({"error": "Impossible de se battre contre soi-même"}, status_code=422)

    state = normalize_player_state(players[username])
    if state.action_points <= 0:
        return JSONResponse({"error": "PA insuffisants"}, status_code=400)

    state.action_points -= 1
    players[username] = state

    attacker = get_or_create_hero(username)
    defender = get_or_create_hero(opponent)
    rng = Random(f"duel:{username}:{opponent}:{datetime.now(timezone.utc).isoformat()}")
    result = simulate_duel(attacker, defender, rng)

    winner = username if result["winner"] == "attacker" else opponent
    get_or_create_duel_stats(username)
    get_or_create_duel_stats(opponent)
    duel_stats[winner]["wins"] += 1
    loser = opponent if winner == username else username
    duel_stats[loser]["losses"] += 1
    push_community_event("duel", f"{winner} remporte un duel contre {loser}.", actor=winner)

    summary = (
        f"{username} vs {opponent}: vainqueur {winner}. "
        f"Burst VIT {username}={result['attacker_burst']} / {opponent}={result['defender_burst']}."
    )

    await broadcast_states()

    return {
        "action_points": state.action_points,
        "summary": summary,
        "winner": winner,
        "combat": result,
        "duel_stats": get_or_create_duel_stats(username),
        "duel_leaderboard": duel_leaderboard_snapshot(),
    }


@app.get("/api/duels/leaderboard")
async def get_duel_leaderboard():
    return {"leaderboard": duel_leaderboard_snapshot()}

@app.post("/api/equipment/equip")
async def equip_item(username: str = Form(...), item_name: str = Form(...)):
    username = username.strip()
    item_name = item_name.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    hero = get_or_create_hero(username)
    if item_name not in hero.inventory:
        return JSONResponse({"error": "Objet absent de l'inventaire"}, status_code=404)

    item = ITEM_CATALOG.get(item_name)
    if not item or item["slot"] == "consumable":
        return JSONResponse({"error": "Cet objet n'est pas équipable"}, status_code=422)

    hero.equipment[item["slot"]] = item_name
    return {"hero": hero_snapshot(hero)}


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


@app.get("/api/contracts/current")
async def get_current_contract():
    return contract_snapshot()


@app.get("/api/events")
async def get_community_events():
    return {"events": community_events_snapshot()}


@app.post("/api/contracts/contribute")
async def contribute_contract(username: str = Form(...)):
    username = username.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    state = normalize_player_state(players[username])
    if state.action_points <= 0:
        return JSONResponse({"error": "PA insuffisants"}, status_code=400)

    state.action_points -= 1
    players[username] = state

    hero = get_or_create_hero(username)
    contribution = 8 + hero.level + Random(f"contract:{username}:{datetime.now(timezone.utc).isoformat()}").randint(0, 5)
    contract_state["progress"] += contribution
    contract_state["contributors"][username] = contract_state["contributors"].get(username, 0) + contribution

    reward = None
    completed = contract_state["progress"] >= contract_state["goal"]
    if completed:
        reward = {
            "gold": 40 + contract_state["season"] * 5,
            "xp": 25 + contract_state["season"] * 4,
            "contract": contract_state["title"],
        }
        hero.gold += reward["gold"]
        hero.xp += reward["xp"]
        while hero.xp >= 100:
            hero.xp -= 100
            hero.level += 1
            hero.max_hp += 10
            hero.hp = hero.max_hp
        push_community_event("contract", f"{username} finalise le contrat '{reward['contract']}' pour toute la saison.", actor=username)
        rotate_contracts()

    await broadcast_states()

    return {
        "action_points": state.action_points,
        "contribution": contribution,
        "completed": completed,
        "reward": reward,
        "contract": contract_snapshot(),
        "hero": hero_snapshot(hero),
    }


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
        push_community_event(
            "raid",
            f"{username} et la guilde {guild_name} terrassent {defeated_boss['name']} (Niv.{defeated_boss['level']}).",
            actor=username,
        )
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
    push_community_event("guild", f"{username} fonde la guilde {guild_name}.", actor=username)
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
    push_community_event("guild", f"{username} rejoint la guilde {guild_name}.", actor=username)
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
        push_community_event("guild", f"{username} quitte la guilde {guild_name}.", actor=username)
    else:
        guild_members.pop(guild_name, None)
        guild_messages.pop(guild_name, None)
        member_count = 0
        chat = []
        push_community_event("guild", f"{username} dissout la guilde {guild_name}.", actor=username)

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
    await broadcast_states()
    return {
        "guild": guild_name,
        "chat": list(guild_messages[guild_name]),
    }


@app.get("/api/chat/global")
async def get_global_chat():
    return {"chat": list(global_messages)}


@app.post("/api/chat/global")
async def post_global_message(username: str = Form(...), message: str = Form(...)):
    username = username.strip()
    content = message.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if len(content) < 2:
        return JSONResponse({"error": "Message trop court"}, status_code=422)
    if len(content) > 180:
        return JSONResponse({"error": "Message trop long (180 max)"}, status_code=422)

    global_messages.append(
        {
            "author": username,
            "message": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await broadcast_states()
    return {"chat": list(global_messages)}


@app.get("/api/party-board")
async def get_party_board():
    return {"entries": party_board_snapshot()}


@app.post("/api/party-board")
async def post_party_board_entry(
    username: str = Form(...),
    activity: str = Form(...),
    message: str = Form(...),
):
    username = username.strip()
    activity = activity.strip()
    content = message.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if len(activity) < 3:
        return JSONResponse({"error": "Activité trop courte"}, status_code=422)
    if len(activity) > 40:
        return JSONResponse({"error": "Activité trop longue (40 max)"}, status_code=422)
    if len(content) < 6:
        return JSONResponse({"error": "Message trop court (6 minimum)"}, status_code=422)
    if len(content) > 220:
        return JSONResponse({"error": "Message trop long (220 max)"}, status_code=422)

    now = datetime.now(timezone.utc).isoformat()
    party_board.appendleft(
        {
            "author": username,
            "activity": activity,
            "message": content,
            "created_at": now,
        }
    )
    push_community_event("party", f"{username} ouvre un groupe: {activity}.", actor=username)

    await broadcast_states()
    return {"entries": party_board_snapshot()}


@app.delete("/api/party-board")
async def delete_party_board_entries(username: str):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    kept_entries = [entry for entry in party_board if entry["author"] != username]
    if len(kept_entries) == len(party_board):
        return JSONResponse({"error": "Aucune annonce à supprimer"}, status_code=404)

    party_board.clear()
    party_board.extend(kept_entries)
    await broadcast_states()
    return {"entries": party_board_snapshot()}


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
