import asyncio

import app


def test_party_board_post_and_delete_flow():
    app.players.clear()
    app.party_board.clear()

    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")

    posted = asyncio.run(
        app.post_party_board_entry(
            username="alpha",
            activity="Raid Hydre",
            message="Cherche tank + heal pour clean rapide ce soir",
        )
    )
    assert posted["entries"][0]["author"] == "alpha"
    assert posted["entries"][0]["activity"] == "Raid Hydre"

    invalid = asyncio.run(
        app.post_party_board_entry(
            username="alpha",
            activity="Pv",
            message="court",
        )
    )
    assert invalid.status_code == 422

    unknown = asyncio.run(
        app.post_party_board_entry(
            username="ghost",
            activity="Contrat",
            message="Besoin de joueurs motivés",
        )
    )
    assert unknown.status_code == 404

    deleted = asyncio.run(app.delete_party_board_entries(username="alpha"))
    assert deleted["entries"] == []

    missing = asyncio.run(app.delete_party_board_entries(username="alpha"))
    assert missing.status_code == 404

    unknown_delete = asyncio.run(app.delete_party_board_entries(username="ghost"))
    assert unknown_delete.status_code == 404
