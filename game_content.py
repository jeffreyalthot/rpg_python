from __future__ import annotations

ITEM_CATALOG: dict[str, dict[str, str]] = {
    "Épée rouillée": {"slot": "weapon", "image": "/static/items/epee_rouillee.svg", "rarity": "commun"},
    "Potion de soin": {"slot": "consumable", "image": "/static/items/potion_soin.svg", "rarity": "commun"},
    "Cape de voyage": {"slot": "back", "image": "/static/items/cape_voyage.svg", "rarity": "commun"},
    "Rune ancienne": {"slot": "trinket", "image": "/static/items/rune_ancienne.svg", "rarity": "rare"},
    "Talisman poli": {"slot": "trinket", "image": "/static/items/talisman_poli.svg", "rarity": "rare"},
    "Ration de voyage": {"slot": "consumable", "image": "/static/items/ration_voyage.svg", "rarity": "commun"},
    "Herbes médicinales": {"slot": "consumable", "image": "/static/items/herbes_medicinales.svg", "rarity": "commun"},
    "Arc du rôdeur": {"slot": "weapon", "image": "/static/items/arc_rodeur.svg", "rarity": "epique"},
    "Casque d'avant-garde": {"slot": "head", "image": "/static/items/casque_avant_garde.svg", "rarity": "rare"},
    "Gants du faucon": {"slot": "hands", "image": "/static/items/gants_faucon.svg", "rarity": "rare"},
    "Bottes de vent": {"slot": "feet", "image": "/static/items/bottes_vent.svg", "rarity": "rare"},
    "Armure de l'aube": {"slot": "chest", "image": "/static/items/armure_aube.svg", "rarity": "legendaire"},
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
