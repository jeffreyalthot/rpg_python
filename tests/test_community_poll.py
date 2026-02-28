import asyncio

import app


def reset_state():
    app.players.clear()
    app.heroes.clear()
    app.community_events.clear()
    app.poll_state["season"] = 1
    app.poll_state["question"] = app.poll_templates[0]["question"]
    app.poll_state["options"] = list(app.poll_templates[0]["options"])
    app.poll_state["votes"] = {}
    app.poll_state["goal"] = 3


def test_poll_vote_grants_reward_and_blocks_double_vote():
    reset_state()
    app.get_or_create_player("alpha")
    app.get_or_create_hero("alpha")

    voted = asyncio.run(app.vote_community_poll(username="alpha", option_id=1))
    assert voted["reward"]["gold"] == 5
    assert voted["poll"]["personal_vote"] == 1
    assert voted["hero"]["gold"] >= 5

    duplicate = asyncio.run(app.vote_community_poll(username="alpha", option_id=2))
    assert duplicate.status_code == 409


def test_poll_rotates_when_goal_reached():
    reset_state()
    for name in ("alpha", "beta", "gamma"):
        app.get_or_create_player(name)

    first_question = app.poll_state["question"]
    asyncio.run(app.vote_community_poll(username="alpha", option_id=0))
    asyncio.run(app.vote_community_poll(username="beta", option_id=0))
    last_vote = asyncio.run(app.vote_community_poll(username="gamma", option_id=2))

    assert last_vote["rotated"] is True
    assert app.poll_state["season"] == 2
    assert app.poll_state["question"] != first_question
    assert app.poll_state["votes"] == {}
    assert any(event["category"] == "poll" for event in app.community_events)
