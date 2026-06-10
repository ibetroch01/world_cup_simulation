from src.elo import update_elo


def test_elo_update_direction_for_underdog_win():
    new_a, new_b = update_elo(1500, 1700, 1.0, 0.0, k_factor=30)
    assert new_a > 1500
    assert new_b < 1700

