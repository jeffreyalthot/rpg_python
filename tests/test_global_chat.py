import asyncio

import app


def test_global_chat_flow_and_validation():
    app.players.clear()
    app.global_messages.clear()
    app.chat_last_message_at.clear()
    app.chat_last_message_text.clear()

    app.get_or_create_player("alpha")

    sent = asyncio.run(app.post_global_message(username="alpha", message="Salut le monde"))
    assert sent["chat"][-1]["author"] == "alpha"
    assert sent["chat"][-1]["message"] == "Salut le monde"

    fetched = asyncio.run(app.get_global_chat())
    assert fetched["chat"][-1]["message"] == "Salut le monde"

    too_short = asyncio.run(app.post_global_message(username="alpha", message="x"))
    assert too_short.status_code == 422

    unknown = asyncio.run(app.post_global_message(username="ghost", message="bonjour"))
    assert unknown.status_code == 404



def test_global_chat_filters_and_antispam():
    app.players.clear()
    app.global_messages.clear()
    app.chat_last_message_at.clear()
    app.chat_last_message_text.clear()

    app.get_or_create_player("mod")

    first = asyncio.run(app.post_global_message(username="mod", message="Ce boss est merde"))
    assert first["chat"][-1]["message"] == "Ce boss est ***"

    duplicate = asyncio.run(app.post_global_message(username="mod", message="Ce boss est merde"))
    assert duplicate.status_code == 429

    app.chat_last_message_at["mod"] = app.chat_last_message_at["mod"] - app.timedelta(seconds=app.CHAT_MIN_INTERVAL_SECONDS)
    duplicate_after_wait = asyncio.run(app.post_global_message(username="mod", message="Ce boss est merde"))
    assert duplicate_after_wait.status_code == 409
