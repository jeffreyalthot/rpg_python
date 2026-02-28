import asyncio

import app


def reset_state():
    app.players.clear()
    app.heroes.clear()
    app.duel_stats.clear()
    app.player_guilds.clear()
    app.guild_members.clear()
    app.guild_messages.clear()
    app.party_board.clear()
    app.community_events.clear()


def test_get_events_endpoint_returns_feed():
    reset_state()
    app.push_community_event("system", "Boot serveur de test")

    payload = asyncio.run(app.get_community_events())

    assert payload["events"]
    assert payload["events"][0]["message"] == "Boot serveur de test"


def test_duel_and_party_board_push_community_events():
    reset_state()
    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")
    app.get_or_create_hero("alpha")
    app.get_or_create_hero("beta")

    asyncio.run(app.duel_player(username="alpha", opponent="beta"))
    asyncio.run(
        app.post_party_board_entry(
            username="alpha",
            activity="Rush donjon",
            message="Need heal + tank pour 20h",
        )
    )

    categories = [entry["category"] for entry in app.community_events]
    assert "duel" in categories
    assert "party" in categories
