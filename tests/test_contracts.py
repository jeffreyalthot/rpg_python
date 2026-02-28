import asyncio

import app


def reset_state():
    app.players.clear()
    app.heroes.clear()
    app.contract_state["season"] = 1
    app.contract_state["goal"] = 240
    app.contract_state["progress"] = 0
    app.contract_state["title"] = app.contracts_pool[0]["title"]
    app.contract_state["description"] = app.contracts_pool[0]["description"]
    app.contract_state["contributors"] = {}


def test_contract_contribution_consumes_pa_and_updates_progress():
    reset_state()
    app.get_or_create_player("alpha")

    before_pa = app.players["alpha"].action_points
    before_progress = app.contract_state["progress"]

    response = asyncio.run(app.contribute_contract(username="alpha"))

    assert response["action_points"] == before_pa - 1
    assert response["contribution"] > 0
    assert response["contract"]["progress"] > before_progress
    assert response["completed"] is False


def test_contract_completion_rotates_season_and_grants_rewards():
    reset_state()
    app.get_or_create_player("alpha")
    hero = app.get_or_create_hero("alpha")
    hero.level = 1
    hero.xp = 0
    hero.gold = 0

    app.contract_state["goal"] = 1
    app.contract_state["progress"] = 0

    response = asyncio.run(app.contribute_contract(username="alpha"))

    assert response["completed"] is True
    assert response["reward"]["gold"] > 0
    assert response["reward"]["xp"] > 0
    assert app.contract_state["season"] == 2
    assert app.contract_state["progress"] == 0
    assert app.heroes["alpha"].gold >= response["reward"]["gold"]
