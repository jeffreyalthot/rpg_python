import asyncio

import app


def reset_commendation_state():
    app.players.clear()
    app.commendations_received.clear()
    app.commendations_log.clear()
    app.daily_state["progress"] = {}


def test_commendation_flow_and_limits():
    reset_commendation_state()

    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")
    app.get_or_create_player("gamma")
    app.get_or_create_player("delta")
    app.get_or_create_player("epsilon")

    first = asyncio.run(app.commend_player(username="alpha", target_username="beta", reason="lead propre"))
    assert first["target"] == "beta"
    assert first["received"] == 1
    assert first["commendations"]["personal"]["remaining"] == 2

    duplicate = asyncio.run(app.commend_player(username="alpha", target_username="beta"))
    assert duplicate.status_code == 409

    asyncio.run(app.commend_player(username="alpha", target_username="gamma"))
    asyncio.run(app.commend_player(username="alpha", target_username="delta"))

    over_limit = asyncio.run(app.commend_player(username="alpha", target_username="epsilon"))
    assert over_limit.status_code == 429



def test_commendation_validation_and_leaderboard():
    reset_commendation_state()

    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")
    app.get_or_create_player("gamma")

    self_commend = asyncio.run(app.commend_player(username="alpha", target_username="alpha"))
    assert self_commend.status_code == 422

    unknown_target = asyncio.run(app.commend_player(username="alpha", target_username="ghost"))
    assert unknown_target.status_code == 404

    asyncio.run(app.commend_player(username="alpha", target_username="beta"))
    asyncio.run(app.commend_player(username="gamma", target_username="beta"))

    board = asyncio.run(app.get_commendations())
    assert board["leaderboard"][0]["username"] == "beta"
    assert board["leaderboard"][0]["received"] == 2

    personal = asyncio.run(app.get_commendations(username="alpha"))
    assert personal["personal"]["received"] == 0
    assert personal["personal"]["remaining"] == 2
