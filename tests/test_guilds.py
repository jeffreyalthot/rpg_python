import asyncio

import app


def test_create_join_chat_and_leave_guild_flow():
    app.players.clear()
    app.heroes.clear()
    app.player_guilds.clear()
    app.guild_members.clear()
    app.guild_messages.clear()

    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")

    created = asyncio.run(app.create_guild(username="alpha", guild_name="Aether"))
    assert created["guild"] == "Aether"
    assert created["member_count"] == 1

    joined = asyncio.run(app.join_guild(username="beta", guild_name="Aether"))
    assert joined["member_count"] == 2

    chatted = asyncio.run(app.post_guild_message(username="beta", message="Prêt pour le raid"))
    assert chatted["guild"] == "Aether"
    assert chatted["chat"][-1]["author"] == "beta"

    left = asyncio.run(app.leave_guild(username="beta"))
    assert left["guild"] is None
    assert app.player_guilds.get("beta") is None


def test_join_missing_guild_returns_404():
    app.players.clear()
    app.player_guilds.clear()
    app.guild_members.clear()
    app.guild_messages.clear()

    app.get_or_create_player("solo")
    response = asyncio.run(app.join_guild(username="solo", guild_name="Introuvable"))

    assert response.status_code == 404
