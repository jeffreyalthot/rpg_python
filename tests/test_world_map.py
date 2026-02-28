import asyncio
from datetime import datetime, timedelta, timezone

import app
from world_map import (
    BATTLEFIELD_COUNT,
    MERCHANT_COUNT,
    STARTING_VILLAGE_COUNT,
    VILLAGE_COUNT,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    Merchant,
    build_world,
    merchant_position,
)


def test_world_generation_counts():
    world = build_world(seed=1, created_at=datetime.now(timezone.utc))

    assert len(world.starting_villages) == STARTING_VILLAGE_COUNT
    assert len(world.villages) == VILLAGE_COUNT
    assert len(world.battlefields) == BATTLEFIELD_COUNT
    assert len(world.merchants) == MERCHANT_COUNT


def test_merchant_moves_one_tile_per_hour():
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    merchant = Merchant(merchant_id=1, x=100, y=100, dx=1, dy=0)

    x, y = merchant_position(merchant, now=created_at + timedelta(hours=3, minutes=20), created_at=created_at)

    assert (x, y) == (103, 100)


def test_world_endpoint_shape():
    payload = asyncio.run(app.get_world())

    assert payload['width'] == WORLD_WIDTH
    assert payload['height'] == WORLD_HEIGHT
    assert len(payload['starting_villages']) == STARTING_VILLAGE_COUNT
    assert len(payload['villages']) == VILLAGE_COUNT
    assert len(payload['battlefields']) == BATTLEFIELD_COUNT
    assert len(payload['merchants']) == MERCHANT_COUNT
