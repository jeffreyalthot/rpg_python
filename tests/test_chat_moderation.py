import asyncio

import app


def test_reporting_player_triggers_temporary_mute():
    app.players.clear()
    app.global_messages.clear()
    app.chat_reports.clear()
    app.chat_mutes_until.clear()
    app.chat_last_message_at.clear()
    app.chat_last_message_text.clear()

    for name in ("alpha", "beta", "gamma", "target"):
        app.get_or_create_player(name)

    first = asyncio.run(
        app.report_chat_message(
            username="alpha",
            target_username="target",
            reason="Insultes répétées dans le canal global",
        )
    )
    assert first["reports"] == 1
    assert first["muted"] is False

    second = asyncio.run(
        app.report_chat_message(
            username="beta",
            target_username="target",
            reason="Spam massif et hors sujet",
        )
    )
    assert second["reports"] == 2

    third = asyncio.run(
        app.report_chat_message(
            username="gamma",
            target_username="target",
            reason="Harcèlement de joueurs débutants",
        )
    )
    assert third["muted"] is True
    assert "target" in app.chat_mutes_until
    assert app.global_messages[-1]["author"] == "Modération"


def test_muted_player_cannot_send_global_message_until_expiration():
    app.players.clear()
    app.global_messages.clear()
    app.chat_reports.clear()
    app.chat_mutes_until.clear()
    app.chat_last_message_at.clear()
    app.chat_last_message_text.clear()

    app.get_or_create_player("target")
    app.chat_mutes_until["target"] = app.datetime.now(app.timezone.utc) + app.timedelta(minutes=5)

    blocked = asyncio.run(app.post_global_message(username="target", message="Je veux parler"))
    assert blocked.status_code == 423

    app.chat_mutes_until["target"] = app.datetime.now(app.timezone.utc) - app.timedelta(seconds=1)
    allowed = asyncio.run(app.post_global_message(username="target", message="Je peux reparler"))
    assert allowed["chat"][-1]["author"] == "target"
