from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import floor

MAX_ACTION_POINTS = 20
RECHARGE_PER_HOUR = 2


@dataclass
class PlayerState:
    action_points: int = MAX_ACTION_POINTS
    last_recharge_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def normalize_player_state(player: PlayerState, now: datetime | None = None) -> PlayerState:
    now = now or datetime.now(timezone.utc)

    if player.action_points >= MAX_ACTION_POINTS:
        player.last_recharge_at = now
        return player

    elapsed = now - player.last_recharge_at
    if elapsed.total_seconds() < 3600:
        return player

    hours_elapsed = floor(elapsed.total_seconds() / 3600)
    recovered = hours_elapsed * RECHARGE_PER_HOUR
    player.action_points = min(MAX_ACTION_POINTS, player.action_points + recovered)
    player.last_recharge_at = player.last_recharge_at + timedelta(hours=hours_elapsed)

    if player.action_points == MAX_ACTION_POINTS:
        player.last_recharge_at = now

    return player
