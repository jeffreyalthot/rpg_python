from pathlib import Path
from random import Random

from game_content import ITEM_CATALOG
from game_progress import outcome_for_tile


def test_item_catalog_images_exist_and_have_stats():
    for name, meta in ITEM_CATALOG.items():
        for stat in ("atk", "def", "vit", "int"):
            assert stat in meta, f"{name} missing stat {stat}"
            assert isinstance(meta[stat], int), f"{name} stat {stat} should be int"

        image_path = Path(meta["image"].lstrip("/"))
        assert image_path.exists(), f"missing image for {name}: {image_path}"


def test_adventure_drop_table_items_are_known():
    for tile_kind in ("battlefield", "merchant", "village", "starting_village", "plain"):
        for seed in range(40):
            outcome = outcome_for_tile(tile_kind, Random(seed))
            if outcome.item_found is not None:
                assert outcome.item_found in ITEM_CATALOG
