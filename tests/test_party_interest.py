import asyncio

import app


def test_party_interest_toggle_and_event():
    app.players.clear()
    app.party_board.clear()
    app.community_events.clear()
    app.party_entry_counter = 0

    app.get_or_create_player("leader")
    app.get_or_create_player("mate")

    post = asyncio.run(
        app.post_party_board_entry(
            username="leader",
            activity="Donjon des Brumes",
            message="Recherche DPS et support pour run rapide",
        )
    )
    entry = post["entries"][0]
    assert entry["interested_players"] == ["leader"]
    assert entry["interested_count"] == 1

    join = asyncio.run(app.mark_party_interest(username="mate", entry_id=entry["id"]))
    assert join["action"] == "added"
    assert join["entry"]["interested_count"] == 2
    assert "mate" in join["entry"]["interested_players"]
    assert app.community_events[0]["category"] == "party"

    leave = asyncio.run(app.mark_party_interest(username="mate", entry_id=entry["id"]))
    assert leave["action"] == "removed"
    assert leave["entry"]["interested_count"] == 1


def test_party_interest_errors():
    app.players.clear()
    app.party_board.clear()
    app.party_entry_counter = 0

    app.get_or_create_player("leader")
    posted = asyncio.run(
        app.post_party_board_entry(
            username="leader",
            activity="Assaut Titan",
            message="Départ immédiat, besoin tank solide",
        )
    )
    entry_id = posted["entries"][0]["id"]

    missing_user = asyncio.run(app.mark_party_interest(username="ghost", entry_id=entry_id))
    assert missing_user.status_code == 404

    missing_entry = asyncio.run(app.mark_party_interest(username="leader", entry_id=9999))
    assert missing_entry.status_code == 404
