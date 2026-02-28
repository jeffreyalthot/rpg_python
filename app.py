from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
player_presence: Dict[str, dict[str, str]] = {}
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
party_entry_counter = 0
friendships: Dict[str, Set[str]] = {}
pending_friend_requests: Dict[str, Set[str]] = {}
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
CHAT_MIN_INTERVAL_SECONDS = 3
CHAT_BLOCKED_WORDS = ("merde", "con", "connard", "pute")
chat_last_message_at: Dict[str, datetime] = {}
chat_last_message_text: Dict[str, str] = {}
chat_reports: Dict[str, dict] = {}
chat_mutes_until: Dict[str, datetime] = {}
CHAT_REPORT_THRESHOLD = 3
CHAT_MUTE_DURATION_MINUTES = 30
CHAT_REPORT_REASON_MIN_LENGTH = 8
CHAT_REPORT_REASON_MAX_LENGTH = 160
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
poll_templates = [
    {
        "question": "Quel nouveau mode prioritaire pour la prochaine saison ?",
        "options": ["Arène 2v2 classée", "Donjon coop narratif", "Tournoi de guildes hebdomadaire"],
    },
    {
        "question": "Quel événement live voulez-vous ce week-end ?",
        "options": ["Double XP exploration", "Boss mondial légendaire", "Foire marchande et craft"],
    },
    {
        "question": "Quel système social améliorer en priorité ?",
        "options": ["Salon vocal intégré", "Calendrier de guilde", "Mentorat nouveaux joueurs"],
    },
]
poll_state = {
    "season": 1,
    "question": poll_templates[0]["question"],
    "options": list(poll_templates[0]["options"]),
    "votes": {},
    "goal": 8,
    "last_rotation_at": datetime.now(timezone.utc).isoformat(),
}
daily_template = {
    "explore": 3,
    "social": 2,
    "combat": 2,
}
daily_state = {
    "date": datetime.now(timezone.utc).date().isoformat(),
    "targets": dict(daily_template),
    "progress": {},
    "completions": {},
    "last_reset_at": datetime.now(timezone.utc).isoformat(),
}
commendations_received: Dict[str, int] = {}
commendations_log: Dict[str, dict] = {}
MAX_DAILY_COMMENDATIONS = 3
PRESENCE_ALLOWED_STATUSES = {"online", "looking_for_group", "raiding", "dueling", "afk"}
PRESENCE_NOTE_MAX_LENGTH = 60


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


def rotate_poll() -> None:
    next_season = poll_state["season"] + 1
    template = poll_templates[(next_season - 1) % len(poll_templates)]
    poll_state["season"] = next_season
    poll_state["question"] = template["question"]
    poll_state["options"] = list(template["options"])
    poll_state["votes"] = {}
    poll_state["last_rotation_at"] = datetime.now(timezone.utc).isoformat()


def poll_snapshot(username: str | None = None) -> dict:
    counts = [0 for _ in poll_state["options"]]
    for choice in poll_state["votes"].values():
        if 0 <= choice < len(counts):
            counts[choice] += 1

    total_votes = sum(counts)
    leaderboard = [
        {
            "option_id": idx,
            "label": option,
            "votes": counts[idx],
            "percent": round((counts[idx] / total_votes) * 100, 1) if total_votes else 0,
        }
        for idx, option in enumerate(poll_state["options"])
    ]
    leaderboard.sort(key=lambda entry: (-entry["votes"], entry["option_id"]))

    payload = {
        "season": poll_state["season"],
        "question": poll_state["question"],
        "goal": poll_state["goal"],
        "total_votes": total_votes,
        "options": leaderboard,
        "last_rotation_at": poll_state["last_rotation_at"],
    }

    if username:
        payload["personal_vote"] = poll_state["votes"].get(username)

    return payload


def party_board_snapshot() -> list[dict]:
    return [
        {
            "id": entry["id"],
            "author": entry["author"],
            "activity": entry["activity"],
            "message": entry["message"],
            "roles": entry["roles"],
            "min_level": entry["min_level"],
            "max_members": entry["max_members"],
            "created_at": entry["created_at"],
            "interested_count": len(entry["interested_players"]),
            "interested_players": sorted(entry["interested_players"]),
            "ready_count": len(entry["ready_players"]),
            "ready_players": sorted(entry["ready_players"]),
            "is_full": len(entry["interested_players"]) >= entry["max_members"],
            "is_launched": bool(entry.get("is_launched", False)),
            "launched_at": entry.get("launched_at"),
        }
        for entry in party_board
    ]


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


def ensure_daily_cycle() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    if daily_state["date"] == today:
        return

    daily_state["date"] = today
    daily_state["targets"] = dict(daily_template)
    daily_state["progress"] = {}
    daily_state["last_reset_at"] = datetime.now(timezone.utc).isoformat()


def ensure_daily_progress(username: str) -> dict:
    ensure_daily_cycle()
    if username not in daily_state["progress"]:
        daily_state["progress"][username] = {
            "explore": 0,
            "social": 0,
            "combat": 0,
            "claimed": False,
        }
    return daily_state["progress"][username]


def add_daily_progress(username: str, category: str, amount: int = 1) -> None:
    progress = ensure_daily_progress(username)
    target = daily_state["targets"].get(category, 0)
    if target <= 0:
        return
    progress[category] = min(target, progress.get(category, 0) + amount)


def daily_challenge_snapshot(username: str | None = None) -> dict:
    ensure_daily_cycle()
    ranking = [
        {"username": name, "completions": count}
        for name, count in sorted(daily_state["completions"].items(), key=lambda item: (-item[1], item[0].lower()))
    ]

    payload = {
        "date": daily_state["date"],
        "targets": dict(daily_state["targets"]),
        "ranking": ranking[:10],
        "last_reset_at": daily_state["last_reset_at"],
    }
    if username:
        progress = ensure_daily_progress(username)
        completed = all(progress[key] >= daily_state["targets"][key] for key in daily_state["targets"])
        payload["personal"] = {
            "explore": progress["explore"],
            "social": progress["social"],
            "combat": progress["combat"],
            "claimed": progress["claimed"],
            "completed": completed,
        }

    return payload


def commendations_snapshot(username: str | None = None) -> dict:
    ranking = [
        {"username": player, "received": total}
        for player, total in sorted(
            commendations_received.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )
        if total > 0
    ]

    payload = {
        "daily_limit": MAX_DAILY_COMMENDATIONS,
        "leaderboard": ranking[:10],
    }

    if username:
        today = datetime.now(timezone.utc).date().isoformat()
        actor_state = commendations_log.get(username, {"date": today, "targets": set()})
        if actor_state["date"] != today:
            actor_state = {"date": today, "targets": set()}

        payload["personal"] = {
            "remaining": max(0, MAX_DAILY_COMMENDATIONS - len(actor_state["targets"])),
            "already_commended": sorted(actor_state["targets"]),
            "received": commendations_received.get(username, 0),
        }

    return payload


def get_or_create_commendation_state(username: str) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    if username not in commendations_log or commendations_log[username]["date"] != today:
        commendations_log[username] = {"date": today, "targets": set()}
    return commendations_log[username]


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


def get_or_create_player(username: str) -> PlayerState:
    if username not in players:
        players[username] = PlayerState(action_points=MAX_ACTION_POINTS, last_recharge_at=datetime.now(timezone.utc))
    player_presence.setdefault(username, {"status": "online", "note": ""})
    return normalize_player_state(players[username])


def get_or_create_hero(username: str) -> HeroProfile:
    if username not in heroes:
        heroes[username] = HeroProfile()
    ensure_social_profile(username)
    return heroes[username]


def ensure_social_profile(username: str) -> None:
    friendships.setdefault(username, set())
    pending_friend_requests.setdefault(username, set())


def social_snapshot(username: str) -> dict:
    ensure_social_profile(username)
    friends = [
        {
            "username": friend,
            "online": friend in players,
            "presence": player_presence.get(friend, {"status": "offline", "note": ""}),
        }
        for friend in sorted(friendships[username], key=str.lower)
    ]
    incoming = sorted(pending_friend_requests.get(username, set()), key=str.lower)
    outgoing = sorted(
        recipient
        for recipient, requesters in pending_friend_requests.items()
        if username in requesters
    )
    return {
        "friends": friends,
        "incoming_requests": incoming,
        "outgoing_requests": outgoing,
    }


def sanitize_chat_message(message: str) -> str:
    sanitized = message
    for blocked_word in CHAT_BLOCKED_WORDS:
        sanitized = sanitized.replace(blocked_word, "***")
        sanitized = sanitized.replace(blocked_word.capitalize(), "***")
        sanitized = sanitized.replace(blocked_word.upper(), "***")
    return sanitized


def validate_chat_message(username: str, content: str) -> JSONResponse | None:
    mute_until = chat_mutes_until.get(username)
    if mute_until and mute_until > datetime.now(timezone.utc):
        remaining_seconds = int((mute_until - datetime.now(timezone.utc)).total_seconds())
        return JSONResponse(
            {
                "error": f"Canal verrouillé: vous pourrez parler dans {max(1, remaining_seconds)}s",
                "muted_until": mute_until.isoformat(),
            },
            status_code=423,
        )
    if mute_until and mute_until <= datetime.now(timezone.utc):
        chat_mutes_until.pop(username, None)

    now = datetime.now(timezone.utc)
    last_sent_at = chat_last_message_at.get(username)
    if last_sent_at is not None:
        elapsed_seconds = (now - last_sent_at).total_seconds()
        if elapsed_seconds < CHAT_MIN_INTERVAL_SECONDS:
            wait_seconds = CHAT_MIN_INTERVAL_SECONDS - elapsed_seconds
            return JSONResponse(
                {"error": f"Anti-spam actif: attendez encore {wait_seconds:.1f}s"},
                status_code=429,
            )

    previous_message = chat_last_message_text.get(username)
    if previous_message and previous_message.casefold() == content.casefold():
        return JSONResponse(
            {"error": "Message dupliqué: variez votre message avant de le renvoyer"},
            status_code=409,
        )

    chat_last_message_at[username] = now
    chat_last_message_text[username] = content
    return None


def chat_moderation_snapshot(username: str | None = None) -> dict:
    payload = {
        "report_threshold": CHAT_REPORT_THRESHOLD,
        "mute_duration_minutes": CHAT_MUTE_DURATION_MINUTES,
    }
    if username:
        muted_until = chat_mutes_until.get(username)
        active = muted_until is not None and muted_until > datetime.now(timezone.utc)
        if muted_until is not None and muted_until <= datetime.now(timezone.utc):
            chat_mutes_until.pop(username, None)
            muted_until = None
            active = False
        payload["personal"] = {
            "is_muted": active,
            "muted_until": muted_until.isoformat() if muted_until else None,
        }
    return payload


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
                "presence": player_presence.get(name, {"status": "online", "note": ""}),
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
        "daily": daily_challenge_snapshot(),
        "poll": poll_snapshot(),
        "commendations": commendations_snapshot(),
        "moderation": chat_moderation_snapshot(),
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
    player_presence[username] = {"status": "online", "note": ""}
    hero = get_or_create_hero(username)
    ensure_social_profile(username)
    ensure_daily_progress(username)
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
        "social": social_snapshot(username),
        "presence": player_presence[username],
        "daily": daily_challenge_snapshot(username),
        "poll": poll_snapshot(username),
        "commendations": commendations_snapshot(username),
        "moderation": chat_moderation_snapshot(username),
    }


@app.post("/api/presence")
async def update_presence(username: str = Form(...), status: str = Form(...), note: str = Form("")):
    username = username.strip()
    status = status.strip().lower()
    note = note.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if status not in PRESENCE_ALLOWED_STATUSES:
        return JSONResponse({"error": "Statut invalide"}, status_code=422)
    if len(note) > PRESENCE_NOTE_MAX_LENGTH:
        return JSONResponse({"error": f"Note trop longue ({PRESENCE_NOTE_MAX_LENGTH} max)"}, status_code=422)

    player_presence[username] = {"status": status, "note": note}
    add_daily_progress(username, "social")
    await broadcast_states()
    return {
        "username": username,
        "presence": player_presence[username],
        "social": social_snapshot(username),
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
    add_daily_progress(username, "explore")

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
    add_daily_progress(username, "combat")
    add_daily_progress(opponent, "combat")
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


@app.get("/api/community/poll")
async def get_community_poll(username: str | None = None):
    normalized = username.strip() if username else None
    if normalized and normalized not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    return poll_snapshot(normalized)


@app.post("/api/community/poll/vote")
async def vote_community_poll(username: str = Form(...), option_id: int = Form(...)):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if option_id < 0 or option_id >= len(poll_state["options"]):
        return JSONResponse({"error": "Option de vote invalide"}, status_code=422)
    if username in poll_state["votes"]:
        return JSONResponse({"error": "Vous avez déjà voté pour cette saison"}, status_code=409)

    poll_state["votes"][username] = option_id
    add_daily_progress(username, "social")

    hero = get_or_create_hero(username)
    hero.gold += 5

    should_rotate = len(poll_state["votes"]) >= poll_state["goal"]
    winning_option = None
    if should_rotate:
        current = poll_snapshot()
        if current["options"]:
            winning_option = current["options"][0]["label"]
        push_community_event(
            "poll",
            f"Sondage saison {poll_state['season']} clos: '{winning_option}' arrive en tête.",
            actor=username,
        )
        rotate_poll()

    await broadcast_states()

    return {
        "reward": {"gold": 5},
        "hero": hero_snapshot(hero),
        "rotated": should_rotate,
        "winning_option": winning_option,
        "poll": poll_snapshot(username),
    }


@app.get("/api/daily")
async def get_daily_challenge(username: str | None = None):
    normalized = username.strip() if username else None
    if normalized and normalized not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    return daily_challenge_snapshot(normalized)


@app.post("/api/daily/claim")
async def claim_daily_challenge(username: str = Form(...)):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    progress = ensure_daily_progress(username)
    completed = all(progress[key] >= daily_state["targets"][key] for key in daily_state["targets"])
    if not completed:
        return JSONResponse({"error": "Défi quotidien incomplet"}, status_code=409)
    if progress["claimed"]:
        return JSONResponse({"error": "Récompense déjà récupérée"}, status_code=409)

    hero = get_or_create_hero(username)
    state = normalize_player_state(players[username])
    reward = {
        "gold": 35,
        "xp": 20,
        "action_points": 2,
    }

    hero.gold += reward["gold"]
    hero.xp += reward["xp"]
    while hero.xp >= 100:
        hero.xp -= 100
        hero.level += 1
        hero.max_hp += 10
        hero.hp = hero.max_hp

    state.action_points = min(MAX_ACTION_POINTS, state.action_points + reward["action_points"])
    players[username] = state
    progress["claimed"] = True
    daily_state["completions"][username] = daily_state["completions"].get(username, 0) + 1
    push_community_event("daily", f"{username} valide son défi quotidien et motive la communauté.", actor=username)

    await broadcast_states()
    return {
        "reward": reward,
        "hero": hero_snapshot(hero),
        "action_points": state.action_points,
        "daily": daily_challenge_snapshot(username),
    }


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
    add_daily_progress(username, "combat")

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
    add_daily_progress(username, "combat")

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

    chat_error = validate_chat_message(username, content)
    if chat_error is not None:
        return chat_error

    sanitized_content = sanitize_chat_message(content)

    guild_messages.setdefault(guild_name, deque(maxlen=MAX_GUILD_MESSAGES)).append(
        {
            "author": username,
            "message": sanitized_content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    add_daily_progress(username, "social")
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

    chat_error = validate_chat_message(username, content)
    if chat_error is not None:
        return chat_error

    sanitized_content = sanitize_chat_message(content)

    global_messages.append(
        {
            "author": username,
            "message": sanitized_content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    add_daily_progress(username, "social")
    await broadcast_states()
    return {"chat": list(global_messages)}


@app.post("/api/chat/report")
async def report_chat_message(username: str = Form(...), target_username: str = Form(...), reason: str = Form(...)):
    username = username.strip()
    target_username = target_username.strip()
    reason = reason.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if target_username not in players:
        return JSONResponse({"error": "Cible inconnue"}, status_code=404)
    if username == target_username:
        return JSONResponse({"error": "Impossible de signaler votre propre message"}, status_code=422)
    if len(reason) < CHAT_REPORT_REASON_MIN_LENGTH:
        return JSONResponse(
            {"error": f"Motif trop court ({CHAT_REPORT_REASON_MIN_LENGTH} min)"},
            status_code=422,
        )
    if len(reason) > CHAT_REPORT_REASON_MAX_LENGTH:
        return JSONResponse(
            {"error": f"Motif trop long ({CHAT_REPORT_REASON_MAX_LENGTH} max)"},
            status_code=422,
        )

    report_state = chat_reports.setdefault(target_username, {"reporters": set(), "reasons": deque(maxlen=8)})
    if username in report_state["reporters"]:
        return JSONResponse({"error": "Vous avez déjà signalé ce joueur récemment"}, status_code=409)

    report_state["reporters"].add(username)
    report_state["reasons"].append(
        {
            "reporter": username,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    muted = False
    if len(report_state["reporters"]) >= CHAT_REPORT_THRESHOLD:
        muted = True
        mute_until = datetime.now(timezone.utc) + timedelta(minutes=CHAT_MUTE_DURATION_MINUTES)
        chat_mutes_until[target_username] = mute_until
        report_state["reporters"] = set()
        global_messages.append(
            {
                "author": "Modération",
                "message": f"{target_username} est temporairement muet suite à plusieurs signalements.",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        push_community_event(
            "moderation",
            f"Le canal mondial applique un mute temporaire à {target_username} après signalements.",
            actor=target_username,
        )
        await broadcast_states()

    return {
        "target": target_username,
        "reports": len(report_state["reporters"]),
        "threshold": CHAT_REPORT_THRESHOLD,
        "muted": muted,
        "moderation": chat_moderation_snapshot(username),
    }


@app.get("/api/party-board")
async def get_party_board():
    return {"entries": party_board_snapshot()}


@app.post("/api/party-board")
async def post_party_board_entry(
    username: str = Form(...),
    activity: str = Form(...),
    message: str = Form(...),
    roles: str = Form("Tous rôles"),
    min_level: int = Form(1),
    max_members: int = Form(4),
):
    global party_entry_counter
    username = username.strip()
    activity = activity.strip()
    content = message.strip()
    roles = roles if isinstance(roles, str) else "Tous rôles"
    roles = roles.strip()
    min_level = min_level if isinstance(min_level, int) else 1
    max_members = max_members if isinstance(max_members, int) else 4

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
    if len(roles) < 3:
        return JSONResponse({"error": "Les rôles doivent contenir au moins 3 caractères"}, status_code=422)
    if len(roles) > 60:
        return JSONResponse({"error": "Les rôles sont limités à 60 caractères"}, status_code=422)
    if min_level < 1 or min_level > 60:
        return JSONResponse({"error": "Niveau minimum invalide (1 à 60)"}, status_code=422)
    if max_members < 2 or max_members > 8:
        return JSONResponse({"error": "Taille du groupe invalide (2 à 8)"}, status_code=422)

    now = datetime.now(timezone.utc).isoformat()
    party_entry_counter += 1
    party_board.appendleft(
        {
            "id": party_entry_counter,
            "author": username,
            "activity": activity,
            "message": content,
            "roles": roles,
            "min_level": min_level,
            "max_members": max_members,
            "created_at": now,
            "interested_players": {username},
            "ready_players": {username},
            "is_launched": False,
            "launched_at": None,
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


@app.post("/api/party-board/interest")
async def mark_party_interest(username: str = Form(...), entry_id: int = Form(...)):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    entry = next((current for current in party_board if current["id"] == entry_id), None)
    if entry is None:
        return JSONResponse({"error": "Annonce introuvable"}, status_code=404)

    interested = entry["interested_players"]
    ready_players = entry["ready_players"]
    if username in interested:
        interested.discard(username)
        ready_players.discard(username)
        action = "removed"
    else:
        if entry.get("is_launched"):
            return JSONResponse({"error": "Ce groupe est déjà verrouillé et lancé"}, status_code=409)
        if len(interested) >= entry["max_members"]:
            return JSONResponse({"error": "Ce groupe est déjà complet"}, status_code=409)
        interested.add(username)
        action = "added"
        if username != entry["author"]:
            push_community_event("party", f"{username} rejoint le groupe '{entry['activity']}'.", actor=username)

    await broadcast_states()
    return {
        "action": action,
        "entry": {
            "id": entry["id"],
            "interested_count": len(interested),
            "interested_players": sorted(interested),
        },
        "entries": party_board_snapshot(),
    }


@app.post("/api/party-board/ready")
async def toggle_party_ready(username: str = Form(...), entry_id: int = Form(...)):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    entry = next((current for current in party_board if current["id"] == entry_id), None)
    if entry is None:
        return JSONResponse({"error": "Annonce introuvable"}, status_code=404)
    if entry.get("is_launched"):
        return JSONResponse({"error": "Le groupe est déjà lancé"}, status_code=409)

    interested = entry["interested_players"]
    ready_players = entry["ready_players"]
    if username not in interested:
        return JSONResponse({"error": "Rejoignez d'abord ce groupe pour vous déclarer prêt"}, status_code=409)

    if username in ready_players:
        ready_players.discard(username)
        action = "unready"
    else:
        ready_players.add(username)
        action = "ready"

    await broadcast_states()
    return {
        "action": action,
        "entry": {
            "id": entry["id"],
            "ready_count": len(ready_players),
            "ready_players": sorted(ready_players),
            "interested_count": len(interested),
            "interested_players": sorted(interested),
        },
        "entries": party_board_snapshot(),
    }


@app.post("/api/party-board/launch")
async def launch_party_group(username: str = Form(...), entry_id: int = Form(...)):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    entry = next((current for current in party_board if current["id"] == entry_id), None)
    if entry is None:
        return JSONResponse({"error": "Annonce introuvable"}, status_code=404)
    if entry["author"] != username:
        return JSONResponse({"error": "Seul le leader peut lancer ce groupe"}, status_code=403)
    if entry.get("is_launched"):
        return JSONResponse({"error": "Ce groupe a déjà été lancé"}, status_code=409)

    interested = entry["interested_players"]
    ready_players = entry["ready_players"]
    if len(interested) < 2:
        return JSONResponse({"error": "Il faut au moins 2 joueurs pour lancer un groupe"}, status_code=422)

    missing_ready = sorted(interested - ready_players)
    if missing_ready:
        return JSONResponse(
            {
                "error": "Tous les joueurs doivent être prêts avant le lancement",
                "missing_ready": missing_ready,
            },
            status_code=409,
        )

    entry["is_launched"] = True
    entry["launched_at"] = datetime.now(timezone.utc).isoformat()
    push_community_event(
        "party",
        f"{username} lance le groupe '{entry['activity']}' avec {len(interested)} joueurs prêts.",
        actor=username,
    )

    await broadcast_states()
    return {
        "entry": {
            "id": entry["id"],
            "is_launched": True,
            "launched_at": entry["launched_at"],
            "interested_players": sorted(interested),
            "ready_players": sorted(ready_players),
        },
        "entries": party_board_snapshot(),
    }


@app.get("/api/friends")
async def get_friends(username: str):
    username = username.strip()
    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    return social_snapshot(username)


@app.post("/api/friends/request")
async def send_friend_request(username: str = Form(...), target_username: str = Form(...)):
    username = username.strip()
    target_username = target_username.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if not target_username:
        return JSONResponse({"error": "Pseudo cible invalide"}, status_code=422)
    if target_username == username:
        return JSONResponse({"error": "Impossible de s'ajouter soi-même"}, status_code=422)
    if get_user_by_username(target_username) is None:
        return JSONResponse({"error": "Joueur cible introuvable"}, status_code=404)

    ensure_social_profile(username)
    ensure_social_profile(target_username)

    if target_username in friendships[username]:
        return JSONResponse({"error": "Ce joueur est déjà dans votre liste d'amis"}, status_code=409)

    if username in pending_friend_requests[target_username]:
        return JSONResponse({"error": "Demande déjà envoyée"}, status_code=409)

    if target_username in pending_friend_requests[username]:
        pending_friend_requests[username].discard(target_username)
        friendships[username].add(target_username)
        friendships[target_username].add(username)
        push_community_event("social", f"{username} et {target_username} deviennent alliés.", actor=username)
        await broadcast_states()
        return {"status": "accepted", "social": social_snapshot(username)}

    pending_friend_requests[target_username].add(username)
    await broadcast_states()
    return {"status": "sent", "social": social_snapshot(username)}


@app.post("/api/friends/respond")
async def respond_friend_request(username: str = Form(...), requester_username: str = Form(...), action: str = Form(...)):
    username = username.strip()
    requester_username = requester_username.strip()
    decision = action.strip().lower()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if decision not in {"accept", "reject"}:
        return JSONResponse({"error": "Action invalide"}, status_code=422)

    ensure_social_profile(username)
    ensure_social_profile(requester_username)

    if requester_username not in pending_friend_requests[username]:
        return JSONResponse({"error": "Demande introuvable"}, status_code=404)

    pending_friend_requests[username].discard(requester_username)
    if decision == "accept":
        friendships[username].add(requester_username)
        friendships[requester_username].add(username)
        push_community_event("social", f"{username} accepte l'alliance de {requester_username}.", actor=username)

    await broadcast_states()
    return {"status": decision, "social": social_snapshot(username)}


@app.delete("/api/friends")
async def remove_friend(username: str, target_username: str):
    username = username.strip()
    target_username = target_username.strip()

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)

    ensure_social_profile(username)
    ensure_social_profile(target_username)

    if target_username not in friendships[username]:
        return JSONResponse({"error": "Ce joueur ne fait pas partie de vos alliés"}, status_code=404)

    friendships[username].discard(target_username)
    friendships[target_username].discard(username)
    await broadcast_states()
    return {"social": social_snapshot(username)}


@app.get("/api/social/commendations")
async def get_commendations(username: str | None = None):
    normalized = username.strip() if username else None
    if normalized and normalized not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    return commendations_snapshot(normalized)


@app.post("/api/social/commend")
async def commend_player(username: str = Form(...), target_username: str = Form(...), reason: str = Form("")):
    username = username.strip()
    target_username = target_username.strip()
    reason = reason.strip() if isinstance(reason, str) else ""

    if username not in players:
        return JSONResponse({"error": "Joueur inconnu"}, status_code=404)
    if target_username not in players:
        return JSONResponse({"error": "Joueur cible inconnu"}, status_code=404)
    if target_username == username:
        return JSONResponse({"error": "Impossible de se recommander soi-même"}, status_code=422)
    if len(reason) > 80:
        return JSONResponse({"error": "Raison trop longue (80 max)"}, status_code=422)

    actor_state = get_or_create_commendation_state(username)
    if target_username in actor_state["targets"]:
        return JSONResponse({"error": "Vous avez déjà recommandé ce joueur aujourd'hui"}, status_code=409)
    if len(actor_state["targets"]) >= MAX_DAILY_COMMENDATIONS:
        return JSONResponse({"error": "Limite quotidienne de recommandations atteinte"}, status_code=429)

    actor_state["targets"].add(target_username)
    commendations_received[target_username] = commendations_received.get(target_username, 0) + 1
    add_daily_progress(username, "social")

    event_message = f"{username} recommande {target_username} pour son esprit d'équipe."
    if reason:
        event_message = f"{username} recommande {target_username}: {reason}"
    push_community_event("social", event_message, actor=username)

    await broadcast_states()
    return {
        "target": target_username,
        "received": commendations_received[target_username],
        "commendations": commendations_snapshot(username),
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
