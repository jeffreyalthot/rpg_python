import asyncio

import app
from game_progress import HeroProfile, duel_burst_count, simulate_duel


def reset_state():
    app.players.clear()
    app.heroes.clear()


def test_duel_burst_count_is_proportional_to_vit():
    assert duel_burst_count(5, 5) == 1
    assert duel_burst_count(10, 5) == 2
    assert duel_burst_count(17, 5) == 4


def test_simulate_duel_returns_burst_metadata():
    attacker = HeroProfile(level=5)
    defender = HeroProfile(level=2)

    result = simulate_duel(attacker, defender, app.Random('seed'))

    assert result['attacker_burst'] >= 1
    assert result['defender_burst'] >= 1
    assert result['winner'] in {'attacker', 'defender'}


def test_duel_endpoint_consumes_action_points():
    reset_state()
    app.get_or_create_player('alice')
    app.get_or_create_player('bob')
    app.get_or_create_hero('alice')
    app.get_or_create_hero('bob')

    before_pa = app.players['alice'].action_points
    response = asyncio.run(app.duel_player(username='alice', opponent='bob'))

    assert response['action_points'] == before_pa - 1
    assert response['winner'] in {'alice', 'bob'}
    assert 'Burst VIT' in response['summary']
