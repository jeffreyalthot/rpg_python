import asyncio

import app


def reset_social_state():
    app.players.clear()
    app.friendships.clear()
    app.pending_friend_requests.clear()


def fake_user_lookup(username: str):
    return {"username": username} if username in {"alpha", "beta", "gamma"} else None


def test_friend_request_accept_and_remove_flow():
    reset_social_state()
    app.get_user_by_username = fake_user_lookup
    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")

    sent = asyncio.run(app.send_friend_request(username="alpha", target_username="beta"))
    assert sent["status"] == "sent"
    assert "beta" in sent["social"]["outgoing_requests"]

    accepted = asyncio.run(app.respond_friend_request(username="beta", requester_username="alpha", action="accept"))
    assert accepted["status"] == "accept"
    assert accepted["social"]["friends"][0]["username"] == "alpha"

    alpha_social = asyncio.run(app.get_friends(username="alpha"))
    assert alpha_social["friends"][0]["username"] == "beta"

    removed = asyncio.run(app.remove_friend(username="alpha", target_username="beta"))
    assert removed["social"]["friends"] == []


def test_friend_request_validation_and_reject_flow():
    reset_social_state()
    app.get_user_by_username = fake_user_lookup
    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")

    self_request = asyncio.run(app.send_friend_request(username="alpha", target_username="alpha"))
    assert self_request.status_code == 422

    first = asyncio.run(app.send_friend_request(username="alpha", target_username="beta"))
    assert first["status"] == "sent"

    duplicate = asyncio.run(app.send_friend_request(username="alpha", target_username="beta"))
    assert duplicate.status_code == 409

    rejected = asyncio.run(app.respond_friend_request(username="beta", requester_username="alpha", action="reject"))
    assert rejected["status"] == "reject"
    assert rejected["social"]["friends"] == []

    missing = asyncio.run(app.respond_friend_request(username="beta", requester_username="gamma", action="accept"))
    assert missing.status_code == 404
