from src.poisson_model import expected_goals


def test_equal_elo_gives_equal_goal_lambda():
    lambda_a, lambda_b = expected_goals(1800, 1800, total_expected_goals=2.70, damping=800)
    assert lambda_a == lambda_b


def test_lambdas_sum_to_total_expected_goals():
    lambda_a, lambda_b = expected_goals(1900, 1700, total_expected_goals=2.70, damping=800)
    assert abs((lambda_a + lambda_b) - 2.70) < 1e-12

