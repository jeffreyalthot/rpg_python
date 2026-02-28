import asyncio

import app


def reset_state():
    app.players.clear()
    app.heroes.clear()
    app.player_guilds.clear()
    app.guild_members.clear()
    app.guild_messages.clear()
    app.reset_raid(1)


def test_attack_raid_requires_guild_membership():
    reset_state()
    app.get_or_create_player("solo")

    response = asyncio.run(app.attack_raid_boss(username="solo"))

    assert response.status_code == 409


def test_attack_raid_consumes_action_points_and_updates_ranking():
    reset_state()
    app.get_or_create_player("alpha")

    asyncio.run(app.create_guild(username="alpha", guild_name="Raiders"))
    before_pa = app.players["alpha"].action_points
    before_hp = app.raid_state["hp"]

    response = asyncio.run(app.attack_raid_boss(username="alpha"))

    assert response["damage"] > 0
    assert response["action_points"] == before_pa - 1
    assert response["raid"]["hp"] < before_hp
    assert response["raid"]["ranking"][0]["guild"] == "Raiders"
