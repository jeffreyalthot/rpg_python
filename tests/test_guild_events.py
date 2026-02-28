import asyncio
from datetime import datetime, timedelta, timezone

import app


def reset_state():
    app.players.clear()
    app.heroes.clear()
    app.player_guilds.clear()
    app.guild_members.clear()
    app.guild_messages.clear()
    app.guild_events.clear()
    app.community_events.clear()
    app.guild_event_counter = 0


def test_create_guild_event_and_rsvp_flow():
    reset_state()
    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")

    asyncio.run(app.create_guild(username="alpha", guild_name="Aether"))
    asyncio.run(app.join_guild(username="beta", guild_name="Aether"))

    starts_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    created = asyncio.run(
        app.create_guild_event(
            username="alpha",
            title="Raid Hydre HM",
            starts_at=starts_at,
            note="Tank + 2 supports requis",
        )
    )

    assert created["guild"] == "Aether"
    assert len(created["events"]) == 1
    assert created["events"][0]["attending_count"] == 1

    event_id = created["events"][0]["id"]
    updated = asyncio.run(app.rsvp_guild_event(username="beta", event_id=event_id, response="maybe"))

    assert updated["events"][0]["maybe_count"] == 1
    assert updated["events"][0]["attending_count"] == 1


def test_create_guild_event_requires_guild_membership():
    reset_state()
    app.get_or_create_player("solo")

    starts_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = asyncio.run(
        app.create_guild_event(
            username="solo",
            title="Sortie donjon",
            starts_at=starts_at,
            note="",
        )
    )

    assert response.status_code == 409


def test_leaving_guild_removes_player_rsvp():
    reset_state()
    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")

    asyncio.run(app.create_guild(username="alpha", guild_name="Sentinels"))
    asyncio.run(app.join_guild(username="beta", guild_name="Sentinels"))

    starts_at = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    created = asyncio.run(app.create_guild_event(username="alpha", title="Run contrat", starts_at=starts_at, note=""))
    event_id = created["events"][0]["id"]
    asyncio.run(app.rsvp_guild_event(username="beta", event_id=event_id, response="attending"))

    leave_payload = asyncio.run(app.leave_guild(username="beta"))
    assert leave_payload["guild"] is None

    snapshot = app.guild_events_snapshot("Sentinels")
    assert snapshot[0]["attending_count"] == 1
