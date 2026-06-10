from src.config import SimulationConfig
from src.data_loader import load_all_data
from src.simulation import run_simulations, simulate_sample_by_index


def test_sample_by_index_matches_first_batch_sample():
    teams, elos, slots, mapping = load_all_data()
    config = SimulationConfig(random_seed=123)
    _, _, first_sample = run_simulations(3, teams, elos, slots, mapping, config)
    selected_sample = simulate_sample_by_index(1, teams, elos, slots, mapping, config)

    assert selected_sample.champion == first_sample.champion
    assert [(m.match_id, m.team_a, m.team_b, m.goals_a, m.goals_b, m.winner) for m in selected_sample.matches] == [
        (m.match_id, m.team_a, m.team_b, m.goals_a, m.goals_b, m.winner) for m in first_sample.matches
    ]


def test_finish_probabilities_sum_to_one_per_team():
    teams, elos, slots, mapping = load_all_data()
    config = SimulationConfig(random_seed=456)
    probability_table, _, _ = run_simulations(5, teams, elos, slots, mapping, config)
    finish_columns = [column for column in probability_table.columns if column.startswith("P(Finish ")]

    assert len(finish_columns) == 7
    for _, row in probability_table.iterrows():
        assert abs(sum(row[column] for column in finish_columns) - 1.0) < 1e-12
