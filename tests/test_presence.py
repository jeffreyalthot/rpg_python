import asyncio

import app


def reset_presence_state():
    app.players.clear()
    app.player_presence.clear()
    app.friendships.clear()
    app.pending_friend_requests.clear()


def test_update_presence_success_and_friend_snapshot():
    reset_presence_state()
    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")
    app.friendships["alpha"] = {"beta"}
    app.friendships["beta"] = {"alpha"}

    updated = asyncio.run(app.update_presence(username="beta", status="looking_for_group", note="Raid T2 ce soir"))
    assert updated["presence"]["status"] == "looking_for_group"
    assert updated["presence"]["note"] == "Raid T2 ce soir"

    alpha_social = asyncio.run(app.get_friends(username="alpha"))
    assert alpha_social["friends"][0]["presence"]["status"] == "looking_for_group"


def test_update_presence_validation():
    reset_presence_state()
    app.get_or_create_player("alpha")

    invalid_status = asyncio.run(app.update_presence(username="alpha", status="sleeping", note=""))
    assert invalid_status.status_code == 422

    long_note = asyncio.run(app.update_presence(username="alpha", status="afk", note="x" * 61))
    assert long_note.status_code == 422

    unknown = asyncio.run(app.update_presence(username="ghost", status="online", note=""))
    assert unknown.status_code == 404
