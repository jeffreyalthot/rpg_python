from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import floor
from random import Random

WORLD_WIDTH = 5000
WORLD_HEIGHT = 5000
STARTING_VILLAGE_COUNT = 10
VILLAGE_COUNT = 50
BATTLEFIELD_COUNT = 35
MERCHANT_COUNT = 25


@dataclass(frozen=True)
class WorldPoint:
    name: str
    x: int
    y: int


@dataclass(frozen=True)
class Merchant:
    merchant_id: int
    x: int
    y: int
    dx: int
    dy: int


@dataclass
class WorldState:
    starting_villages: list[WorldPoint]
    villages: list[WorldPoint]
    battlefields: list[WorldPoint]
    merchants: list[Merchant]
    created_at: datetime


def _reflect_position(start: int, delta: int, steps: int, max_index: int) -> int:
    if max_index <= 0 or delta == 0 or steps <= 0:
        return start

    period = 2 * max_index
    raw = (start + delta * steps) % period
    if raw <= max_index:
        return raw
    return period - raw


def merchant_position(merchant: Merchant, *, now: datetime, created_at: datetime) -> tuple[int, int]:
    elapsed_seconds = max(0.0, (now - created_at).total_seconds())
    hours_elapsed = floor(elapsed_seconds / 3600)
    x = _reflect_position(merchant.x, merchant.dx, hours_elapsed, WORLD_WIDTH - 1)
    y = _reflect_position(merchant.y, merchant.dy, hours_elapsed, WORLD_HEIGHT - 1)
    return x, y


def build_world(seed: int = 42, created_at: datetime | None = None) -> WorldState:
    rng = Random(seed)
    used: set[tuple[int, int]] = set()

    def unique_position() -> tuple[int, int]:
        while True:
            x = rng.randint(0, WORLD_WIDTH - 1)
            y = rng.randint(0, WORLD_HEIGHT - 1)
            if (x, y) not in used:
                used.add((x, y))
                return x, y

    starting_villages = [
        WorldPoint(name=f"Village départ {i + 1}", x=pos[0], y=pos[1])
        for i in range(STARTING_VILLAGE_COUNT)
        for pos in [unique_position()]
    ]

    villages = [
        WorldPoint(name=f"Village {i + 1}", x=pos[0], y=pos[1])
        for i in range(VILLAGE_COUNT)
        for pos in [unique_position()]
    ]

    battlefields = [
        WorldPoint(name=f"Champ de bataille {i + 1}", x=pos[0], y=pos[1])
        for i in range(BATTLEFIELD_COUNT)
        for pos in [unique_position()]
    ]

    merchants: list[Merchant] = []
    directions = (-1, 0, 1)
    for i in range(MERCHANT_COUNT):
        x, y = unique_position()
        while True:
            dx = rng.choice(directions)
            dy = rng.choice(directions)
            if dx != 0 or dy != 0:
                break
        merchants.append(Merchant(merchant_id=i + 1, x=x, y=y, dx=dx, dy=dy))

    return WorldState(
        starting_villages=starting_villages,
        villages=villages,
        battlefields=battlefields,
        merchants=merchants,
        created_at=created_at or datetime.now(timezone.utc),
    )


def world_snapshot(world: WorldState, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    merchant_positions = [
        {
            "name": f"Marchand ambulant {merchant.merchant_id}",
            "x": pos[0],
            "y": pos[1],
        }
        for merchant in world.merchants
        for pos in [merchant_position(merchant, now=now, created_at=world.created_at)]
    ]

    return {
        "width": WORLD_WIDTH,
        "height": WORLD_HEIGHT,
        "starting_villages": [point.__dict__ for point in world.starting_villages],
        "villages": [point.__dict__ for point in world.villages],
        "battlefields": [point.__dict__ for point in world.battlefields],
        "merchants": merchant_positions,
        "updated_at": now.isoformat(),
    }
