import asyncio

import app
from game_logic import MAX_ACTION_POINTS
from game_progress import AdventureOutcome, HeroProfile, apply_adventure


def test_apply_adventure_level_up_and_item():
    hero = HeroProfile(level=1, xp=95, gold=0, hp=40, max_hp=100, inventory=[])
    outcome = AdventureOutcome(
        summary="Test",
        xp_gain=10,
        gold_gain=5,
        hp_delta=-3,
        item_found="Rune ancienne",
    )

    result = apply_adventure(hero, outcome)

    assert result["level_ups"] == 1
    assert hero.level == 2
    assert hero.xp == 5
    assert hero.gold == 5
    assert hero.hp == hero.max_hp
    assert "Rune ancienne" in hero.inventory


def test_adventure_endpoint_consumes_pa_and_returns_hero():
    app.players.clear()
    app.heroes.clear()

    username = "aventurier"
    app.get_or_create_player(username)
    app.get_or_create_hero(username)

    response = asyncio.run(app.adventure(username=username, tile_kind="battlefield"))

    assert response["username"] == username
    assert response["action_points"] == MAX_ACTION_POINTS - 1
    assert response["hero"]["level"] >= 1
    assert "summary" in response["outcome"]


def test_adventure_requires_existing_player():
    app.players.clear()
    app.heroes.clear()

    response = asyncio.run(app.adventure(username="inconnu", tile_kind="plain"))

    assert response.status_code == 404
