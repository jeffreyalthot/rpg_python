from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from random import Random

from game_content import DEFAULT_EQUIPMENT, ITEM_CATALOG

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


def hero_total_stats(hero: HeroProfile) -> dict[str, int]:
    stats = {
        "atk": 8 + hero.level * 2,
        "def": 6 + hero.level,
        "vit": 5 + hero.level,
        "int": 5 + hero.level,
    }
    for item_name in hero.equipment.values():
        if item_name is None:
            continue
        meta = ITEM_CATALOG.get(item_name)
        if meta is None:
            continue
        for key in stats:
            stats[key] += int(meta.get(key, 0))
    stats["vit"] = max(1, stats["vit"])
    return stats


def duel_burst_count(attacker_vit: int, defender_vit: int) -> int:
    return max(1, ceil(max(1, attacker_vit) / max(1, defender_vit)))


def simulate_duel(attacker: HeroProfile, defender: HeroProfile, rng: Random) -> dict:
    attacker_stats = hero_total_stats(attacker)
    defender_stats = hero_total_stats(defender)
    attacker_hp = attacker.max_hp + attacker_stats["def"] * 2
    defender_hp = defender.max_hp + defender_stats["def"] * 2
    attacker_burst = duel_burst_count(attacker_stats["vit"], defender_stats["vit"])
    defender_burst = duel_burst_count(defender_stats["vit"], attacker_stats["vit"])

    combat_log: list[str] = []
    for _ in range(12):
        for combo in range(attacker_burst):
            damage = max(1, attacker_stats["atk"] + rng.randint(0, attacker_stats["int"] // 2 + 2) - defender_stats["def"] // 2)
            defender_hp = max(0, defender_hp - damage)
            combat_log.append(f"Attaquant combo {combo + 1}/{attacker_burst}: -{damage} PV")
            if defender_hp <= 0:
                return {
                    "winner": "attacker",
                    "log": combat_log,
                    "attacker_remaining_hp": attacker_hp,
                    "defender_remaining_hp": defender_hp,
                    "attacker_stats": attacker_stats,
                    "defender_stats": defender_stats,
                    "attacker_burst": attacker_burst,
                    "defender_burst": defender_burst,
                }

        for combo in range(defender_burst):
            damage = max(1, defender_stats["atk"] + rng.randint(0, defender_stats["int"] // 2 + 2) - attacker_stats["def"] // 2)
            attacker_hp = max(0, attacker_hp - damage)
            combat_log.append(f"Défenseur combo {combo + 1}/{defender_burst}: -{damage} PV")
            if attacker_hp <= 0:
                return {
                    "winner": "defender",
                    "log": combat_log,
                    "attacker_remaining_hp": attacker_hp,
                    "defender_remaining_hp": defender_hp,
                    "attacker_stats": attacker_stats,
                    "defender_stats": defender_stats,
                    "attacker_burst": attacker_burst,
                    "defender_burst": defender_burst,
                }

    winner = "attacker" if attacker_hp >= defender_hp else "defender"
    return {
        "winner": winner,
        "log": combat_log,
        "attacker_remaining_hp": attacker_hp,
        "defender_remaining_hp": defender_hp,
        "attacker_stats": attacker_stats,
        "defender_stats": defender_stats,
        "attacker_burst": attacker_burst,
        "defender_burst": defender_burst,
    }


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
            item_found=rng.choice([None, "Rune ancienne", "Arc du rôdeur", "Casque d'avant-garde", "Lame spectrale"]),
        )

    if tile_kind == "merchant":
        xp = rng.randint(7, 15)
        gold = rng.randint(4, 12)
        return AdventureOutcome(
            "Transaction réussie avec un marchand",
            xp,
            gold,
            0,
            item_found=rng.choice([None, "Talisman poli", "Gants du faucon", "Bottes de vent", "Orbe du stratège"]),
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
            item_found=rng.choice([None, "Ration de voyage", "Armure de l'aube", "Bouclier runique"]),
        )

    xp = rng.randint(9, 20)
    gold = rng.randint(3, 10)
    hp_delta = -rng.randint(0, 6)
    return AdventureOutcome("Exploration des plaines", xp, gold, hp_delta, item_found=rng.choice([None, "Herbes médicinales", "Bottes foudroyantes"]))


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
        "stats": hero_total_stats(hero),
    }
