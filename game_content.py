from __future__ import annotations

ItemMeta = dict[str, str | int]

ITEM_CATALOG: dict[str, ItemMeta] = {
    "Épée rouillée": {"slot": "weapon", "image": "/static/items/epee_rouillee.svg", "rarity": "commun", "atk": 5, "def": 0, "vit": 0, "int": 0},
    "Potion de soin": {"slot": "consumable", "image": "/static/items/potion_soin.svg", "rarity": "commun", "atk": 0, "def": 0, "vit": 0, "int": 1},
    "Cape de voyage": {"slot": "back", "image": "/static/items/cape_voyage.svg", "rarity": "commun", "atk": 0, "def": 2, "vit": 1, "int": 0},
    "Rune ancienne": {"slot": "trinket", "image": "/static/items/rune_ancienne.svg", "rarity": "rare", "atk": 1, "def": 0, "vit": 0, "int": 5},
    "Talisman poli": {"slot": "trinket", "image": "/static/items/talisman_poli.svg", "rarity": "rare", "atk": 0, "def": 1, "vit": 1, "int": 4},
    "Ration de voyage": {"slot": "consumable", "image": "/static/items/ration_voyage.svg", "rarity": "commun", "atk": 0, "def": 0, "vit": 1, "int": 0},
    "Herbes médicinales": {"slot": "consumable", "image": "/static/items/herbes_medicinales.svg", "rarity": "commun", "atk": 0, "def": 0, "vit": 0, "int": 2},
    "Arc du rôdeur": {"slot": "weapon", "image": "/static/items/arc_rodeur.svg", "rarity": "epique", "atk": 9, "def": 0, "vit": 2, "int": 1},
    "Casque d'avant-garde": {"slot": "head", "image": "/static/items/casque_avant_garde.svg", "rarity": "rare", "atk": 0, "def": 5, "vit": 0, "int": 0},
    "Gants du faucon": {"slot": "hands", "image": "/static/items/gants_faucon.svg", "rarity": "rare", "atk": 2, "def": 1, "vit": 2, "int": 0},
    "Bottes de vent": {"slot": "feet", "image": "/static/items/bottes_vent.svg", "rarity": "rare", "atk": 0, "def": 2, "vit": 4, "int": 0},
    "Armure de l'aube": {"slot": "chest", "image": "/static/items/armure_aube.svg", "rarity": "legendaire", "atk": 0, "def": 10, "vit": -1, "int": 2},
    "Lame spectrale": {"slot": "weapon", "image": "/static/items/lame_spectrale.svg", "rarity": "legendaire", "atk": 13, "def": 1, "vit": 3, "int": 2},
    "Bouclier runique": {"slot": "hands", "image": "/static/items/bouclier_runique.svg", "rarity": "epique", "atk": 1, "def": 8, "vit": -1, "int": 3},
    "Bottes foudroyantes": {"slot": "feet", "image": "/static/items/bottes_foudroyantes.svg", "rarity": "epique", "atk": 0, "def": 2, "vit": 7, "int": 0},
    "Orbe du stratège": {"slot": "trinket", "image": "/static/items/orbe_stratege.svg", "rarity": "legendaire", "atk": 0, "def": 2, "vit": 2, "int": 8},
    "Dague de braise": {"slot": "weapon", "image": "/static/items/dague_braise.svg", "rarity": "rare", "atk": 7, "def": 0, "vit": 3, "int": 1},
    "Masse du colosse": {"slot": "weapon", "image": "/static/items/masse_colosse.svg", "rarity": "epique", "atk": 12, "def": 2, "vit": -2, "int": 0},
    "Diadème stellaire": {"slot": "head", "image": "/static/items/diademe_stellaire.svg", "rarity": "legendaire", "atk": 1, "def": 3, "vit": 1, "int": 9},
    "Heaume du rempart": {"slot": "head", "image": "/static/items/heaume_rempart.svg", "rarity": "rare", "atk": 0, "def": 6, "vit": -1, "int": 1},
    "Cuirasse du bastion": {"slot": "chest", "image": "/static/items/cuirasse_bastion.svg", "rarity": "epique", "atk": 0, "def": 11, "vit": -2, "int": 2},
    "Manteau des marées": {"slot": "back", "image": "/static/items/manteau_marees.svg", "rarity": "rare", "atk": 1, "def": 3, "vit": 2, "int": 2},
    "Brassards du cyclone": {"slot": "hands", "image": "/static/items/brassards_cyclone.svg", "rarity": "epique", "atk": 4, "def": 3, "vit": 3, "int": 0},
    "Grèves du gardien": {"slot": "feet", "image": "/static/items/greves_gardien.svg", "rarity": "rare", "atk": 0, "def": 5, "vit": 2, "int": 0},
    "Idole du pacte": {"slot": "trinket", "image": "/static/items/idole_pacte.svg", "rarity": "epique", "atk": 2, "def": 2, "vit": 0, "int": 6},
    "Elixir de zénith": {"slot": "consumable", "image": "/static/items/elixir_zenith.svg", "rarity": "rare", "atk": 0, "def": 0, "vit": 2, "int": 4},
}

DEFAULT_EQUIPMENT = {
    "head": None,
    "chest": None,
    "weapon": "Épée rouillée",
    "back": "Cape de voyage",
    "hands": None,
    "feet": None,
    "trinket": None,
}

CHARACTER_OPTIONS = {
    "hair": ["Court", "Long", "Tresse", "Crête", "Bouclé"],
    "eyes": ["Marron", "Bleu", "Vert", "Gris", "Ambre"],
    "mouth": ["Fin", "Sourire", "Déterminé", "Neutre"],
    "nose": ["Droit", "Aquilin", "Court", "Large"],
    "ears": ["Rondes", "Pointues", "Petites", "Larges"],
    "skin_tone": ["Porcelaine", "Clair", "Doré", "Olive", "Brun", "Ebène"],
}
