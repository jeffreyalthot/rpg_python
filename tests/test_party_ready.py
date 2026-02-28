import asyncio

import app


def test_party_ready_and_launch_flow():
    app.players.clear()
    app.party_board.clear()
    app.party_entry_counter = 0

    app.get_or_create_player("leader")
    app.get_or_create_player("mate")

    posted = asyncio.run(
        app.post_party_board_entry(
            username="leader",
            activity="Raid Titan",
            message="Formation d'une escouade pour boss mondial",
            roles="Tank, DPS",
            max_members=4,
        )
    )
    entry_id = posted["entries"][0]["id"]

    join = asyncio.run(app.mark_party_interest(username="mate", entry_id=entry_id))
    assert join["entry"]["interested_count"] == 2

    launch_blocked = asyncio.run(app.launch_party_group(username="leader", entry_id=entry_id))
    assert launch_blocked.status_code == 409
    assert launch_blocked.body

    ready = asyncio.run(app.toggle_party_ready(username="mate", entry_id=entry_id))
    assert ready["action"] == "ready"
    assert "mate" in ready["entry"]["ready_players"]

    launched = asyncio.run(app.launch_party_group(username="leader", entry_id=entry_id))
    assert launched["entry"]["is_launched"] is True


def test_party_ready_constraints():
    app.players.clear()
    app.party_board.clear()
    app.party_entry_counter = 0

    app.get_or_create_player("leader")
    app.get_or_create_player("mate")
    app.get_or_create_player("outsider")

    posted = asyncio.run(
        app.post_party_board_entry(
            username="leader",
            activity="Donjon Tempête",
            message="Groupe orienté clean rapide",
        )
    )
    entry_id = posted["entries"][0]["id"]

    outsider_ready = asyncio.run(app.toggle_party_ready(username="outsider", entry_id=entry_id))
    assert outsider_ready.status_code == 409

    forbidden_launch = asyncio.run(app.launch_party_group(username="mate", entry_id=entry_id))
    assert forbidden_launch.status_code == 403

    asyncio.run(app.mark_party_interest(username="mate", entry_id=entry_id))
    asyncio.run(app.toggle_party_ready(username="mate", entry_id=entry_id))
    asyncio.run(app.launch_party_group(username="leader", entry_id=entry_id))

    late_join = asyncio.run(app.mark_party_interest(username="outsider", entry_id=entry_id))
    assert late_join.status_code == 409

    late_ready = asyncio.run(app.toggle_party_ready(username="leader", entry_id=entry_id))
    assert late_ready.status_code == 409
