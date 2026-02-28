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
            roles="Tank, Heal",
            min_level=8,
            max_members=3,
        )
    )
    assert posted["entries"][0]["author"] == "alpha"
    assert posted["entries"][0]["activity"] == "Raid Hydre"
    assert posted["entries"][0]["roles"] == "Tank, Heal"
    assert posted["entries"][0]["min_level"] == 8
    assert posted["entries"][0]["max_members"] == 3

    invalid = asyncio.run(
        app.post_party_board_entry(
            username="alpha",
            activity="Pv",
            message="court",
        )
    )
    assert invalid.status_code == 422

    invalid_size = asyncio.run(
        app.post_party_board_entry(
            username="alpha",
            activity="Contrat",
            message="Groupe test pour valider la taille max",
            max_members=10,
        )
    )
    assert invalid_size.status_code == 422

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


def test_party_interest_respects_capacity_limit():
    app.players.clear()
    app.party_board.clear()

    app.get_or_create_player("alpha")
    app.get_or_create_player("beta")
    app.get_or_create_player("gamma")

    posted = asyncio.run(
        app.post_party_board_entry(
            username="alpha",
            activity="Donjon Cendre",
            message="Besoin d'un duo motivé et vocal",
            roles="DPS, Support",
            max_members=2,
        )
    )
    entry_id = posted["entries"][0]["id"]

    joined = asyncio.run(app.mark_party_interest(username="beta", entry_id=entry_id))
    assert joined["action"] == "added"
    assert joined["entry"]["interested_count"] == 2

    full = asyncio.run(app.mark_party_interest(username="gamma", entry_id=entry_id))
    assert full.status_code == 409

    left = asyncio.run(app.mark_party_interest(username="beta", entry_id=entry_id))
    assert left["action"] == "removed"

    joined_after_slot = asyncio.run(app.mark_party_interest(username="gamma", entry_id=entry_id))
    assert joined_after_slot["action"] == "added"
