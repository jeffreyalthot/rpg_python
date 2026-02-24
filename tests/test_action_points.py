from datetime import datetime, timedelta, timezone

from game_logic import MAX_ACTION_POINTS, PlayerState, normalize_player_state


def test_recharge_two_points_per_hour():
    now = datetime.now(timezone.utc)
    player = PlayerState(action_points=10, last_recharge_at=now - timedelta(hours=2, minutes=5))

    normalize_player_state(player, now=now)

    assert player.action_points == 14


def test_cap_to_max_points():
    now = datetime.now(timezone.utc)
    player = PlayerState(action_points=19, last_recharge_at=now - timedelta(hours=3))

    normalize_player_state(player, now=now)

    assert player.action_points == MAX_ACTION_POINTS


def test_no_recharge_before_one_hour():
    now = datetime.now(timezone.utc)
    player = PlayerState(action_points=8, last_recharge_at=now - timedelta(minutes=59))

    normalize_player_state(player, now=now)

    assert player.action_points == 8
