import asyncio

import app


def test_global_chat_flow_and_validation():
    app.players.clear()
    app.global_messages.clear()

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
