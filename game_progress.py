from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from game_content import DEFAULT_EQUIPMENT

XP_PER_LEVEL = 100


@dataclass
class HeroProfile:
    level: int = 1
    xp: int = 0
    gold: int = 90
    hp: int = 100
    max_hp: int = 100
    inventory: list[str] = field(default_factory=lambda: ["Épée rouillée", "Potion de soin", "Cape de voyage"])
    equipment: dict[str, str | None] = field(default_factory=lambda: dict(DEFAULT_EQUIPMENT))


@dataclass
class AdventureOutcome:
    summary: str
    xp_gain: int
    gold_gain: int
    hp_delta: int
    item_found: str | None = None


def outcome_for_tile(tile_kind: str, rng: Random) -> AdventureOutcome:
    if tile_kind == "battlefield":
        xp = rng.randint(18, 34)
        gold = rng.randint(10, 24)
        hp_delta = -rng.randint(8, 20)
        return AdventureOutcome(
            "Escarmouche intense",
            xp,
            gold,
            hp_delta,
            item_found=rng.choice([None, "Rune ancienne", "Arc du rôdeur", "Casque d'avant-garde"]),
        )

    if tile_kind == "merchant":
        xp = rng.randint(7, 15)
        gold = rng.randint(4, 12)
        return AdventureOutcome(
            "Transaction réussie avec un marchand",
            xp,
            gold,
            0,
            item_found=rng.choice([None, "Talisman poli", "Gants du faucon", "Bottes de vent"]),
        )

    if tile_kind in {"village", "starting_village"}:
        xp = rng.randint(8, 16)
        gold = rng.randint(5, 14)
        hp_delta = rng.randint(4, 12)
        return AdventureOutcome(
            "Mission locale accomplie",
            xp,
            gold,
            hp_delta,
            item_found=rng.choice([None, "Ration de voyage", "Armure de l'aube"]),
        )

    xp = rng.randint(9, 20)
    gold = rng.randint(3, 10)
    hp_delta = -rng.randint(0, 6)
    return AdventureOutcome("Exploration des plaines", xp, gold, hp_delta, item_found=rng.choice([None, "Herbes médicinales"]))


def apply_adventure(hero: HeroProfile, outcome: AdventureOutcome) -> dict:
    hero.xp += outcome.xp_gain
    hero.gold += outcome.gold_gain
    hero.hp = max(0, min(hero.max_hp, hero.hp + outcome.hp_delta))

    level_ups = 0
    while hero.xp >= XP_PER_LEVEL:
        hero.xp -= XP_PER_LEVEL
        hero.level += 1
        hero.max_hp += 15
        hero.hp = hero.max_hp
        level_ups += 1

    if outcome.item_found is not None:
        hero.inventory.append(outcome.item_found)

    return {
        "summary": outcome.summary,
        "xp_gain": outcome.xp_gain,
        "gold_gain": outcome.gold_gain,
        "hp_delta": outcome.hp_delta,
        "item_found": outcome.item_found,
        "level_ups": level_ups,
    }


def hero_snapshot(hero: HeroProfile) -> dict:
    return {
        "level": hero.level,
        "xp": hero.xp,
        "gold": hero.gold,
        "hp": hero.hp,
        "max_hp": hero.max_hp,
        "inventory": list(hero.inventory),
        "equipment": dict(hero.equipment),
    }
