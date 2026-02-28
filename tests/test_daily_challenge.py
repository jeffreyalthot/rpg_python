import asyncio
from datetime import datetime, timezone

import app


def reset_daily_state():
    app.daily_state["date"] = datetime.now(timezone.utc).date().isoformat()
    app.daily_state["targets"] = {"explore": 3, "social": 2, "combat": 2}
    app.daily_state["progress"] = {}
    app.daily_state["completions"] = {}
    app.daily_state["last_reset_at"] = datetime.now(timezone.utc).isoformat()


def test_daily_claim_reward_and_ranking():
    app.players.clear()
    app.heroes.clear()
    reset_daily_state()

    app.get_or_create_player("alpha")
    app.get_or_create_hero("alpha")

    app.daily_state["targets"] = {"explore": 1, "social": 1, "combat": 1}
    app.add_daily_progress("alpha", "explore")
    app.add_daily_progress("alpha", "social")
    app.add_daily_progress("alpha", "combat")

    claimed = asyncio.run(app.claim_daily_challenge(username="alpha"))
    assert claimed["reward"]["gold"] == 35
    assert claimed["reward"]["xp"] == 20
    assert claimed["daily"]["personal"]["claimed"] is True
    assert claimed["daily"]["ranking"][0]["username"] == "alpha"
    assert claimed["daily"]["ranking"][0]["completions"] == 1


def test_daily_progress_updates_from_social_and_duel():
    app.players.clear()
    app.heroes.clear()
    app.duel_stats.clear()
    app.global_messages.clear()
    reset_daily_state()

    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")
    app.get_or_create_hero("alpha")
    app.get_or_create_hero("beta")

    posted = asyncio.run(app.post_global_message(username="alpha", message="Salut le monde"))
    assert isinstance(posted["chat"], list)
    assert app.daily_challenge_snapshot("alpha")["personal"]["social"] == 1

    duel = asyncio.run(app.duel_player(username="alpha", opponent="beta"))
    assert duel["winner"] in {"alpha", "beta"}
    assert app.daily_challenge_snapshot("alpha")["personal"]["combat"] == 1
    assert app.daily_challenge_snapshot("beta")["personal"]["combat"] == 1
