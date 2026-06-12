# FIFA World Cup 2026 Attack/Defence Simulator

CLI-first Monte Carlo simulator for the 48-team FIFA World Cup 2026 format. The Streamlit app is a results dashboard only: it reads precomputed output folders and does not train models or run simulations.

## Workflow

Install dependencies:

```bash
pip install -r requirements.txt
```

Build the historical match dataset:

```bash
python scripts/build_historical_matches_dataset.py \
  --start-date 2022-01-01 \
  --output data/historical_matches.csv
```

Train the Attack/Defence model:

```bash
python scripts/train_attack_defence.py \
  --matches data/historical_matches.csv \
  --output-ratings data/team_attack_defence_ratings.csv \
  --output-report data/model_training_report.json \
  --start-date 2022-01-01 \
  --half-life-days 730 \
  --regularization-alpha 0.01
```

Calibrate regularization and strength temperature:

```bash
python scripts/calibrate_strength_temperature.py \
  --matches data/historical_matches.csv \
  --train-start-date 2022-01-01 \
  --train-end-date 2024-12-31 \
  --test-start-date 2025-01-01 \
  --half-life-grid 180,365,500,730 \
  --regularization-grid 0.001,0.01,0.05,0.1 \
  --gamma-grid 0.8,0.9,1.0
```

By default this also runs rolling backtests:

- Train 2022-2023, test 2024
- Train 2022-2024, test 2025
- Train 2022-2025, test 2026 through the latest available match date

The chosen parameters minimize test Poisson NLL. Add `--output-grid data/strength_temperature_grid.csv` if you want to save every fold/grid row.

Run the pre-tournament prediction:

```bash
python scripts/run_simulations.py \
  --runs 100000 \
  --seed 42 \
  --strength-temperature 0.8 \
  --penalty-damping 900 \
  --output-dir outputs/attack_defence_baseline
```

Run the live prediction:

```bash
python scripts/run_simulations.py \
  --runs 100000 \
  --seed 42 \
  --strength-temperature 0.8 \
  --penalty-damping 900 \
  --live-early-prediction \
  --locked-matches data/locked_matches.csv \
  --output-dir outputs/attack_defence_live
```

Start the dashboard:

```bash
streamlit run app.py
```

## Outputs

Each simulation output folder contains:

- `metadata.json`
- `group_phase_results.csv`
- `knockout_phase_results.csv`
- `team_ratings.csv`

The dashboard lets you switch between:

- `outputs/attack_defence_baseline`: World Cup Prediction
- `outputs/attack_defence_live`: Live Prediction

## Live Updates

After a match is played, add its 90-minute score to `data/locked_matches.csv`, rerun the live prediction command, commit the updated CSV and `outputs/attack_defence_live`, then redeploy.

`data/locked_matches.csv` columns:

- `phase`: `group` or `knockout`
- `match_id`: empty for group matches, required for knockout matches
- `group`: required for group matches, empty for knockout matches
- `team_a`, `team_b`: team IDs from `data/teams.csv`
- `goals_a`, `goals_b`: 90-minute goals
- `winner_team`: empty for group matches; required for knockout draws after 90 minutes
- `played_at`: optional date/time used for dashboard metadata

## Model Notes

- This is Monte Carlo simulation, not MCMC.
- The dashboard only displays precomputed outputs.
- World Cup Prediction ignores `data/locked_matches.csv`; Live Prediction uses locked results and simulates only the remaining uncertainty.
- Attack/Defence training uses 2022-now match results with 90-minute scores only.
- Penalty shootout results and extra-time goals are excluded from historical training data.
- Training uses recency weighting, competition weighting, and L2 regularization.
- Calibration selects `half_life_days`, `regularization_alpha`, and `strength_temperature` by holdout Poisson NLL, not by World Cup winner probabilities.
- Current defaults use `regularization_alpha=0.01`, `strength_temperature=0.8`, and `penalty_damping=900`.
- Knockout draws after 90 minutes are resolved by Elo-weighted advancement using `data/initial_elo.csv`.
- The model is simplified and should be validated by backtesting before being treated as reliable.
- Annex C third-place mapping is required for exact bracket correctness. If the mapping CSV is incomplete or invalid, the simulator raises a clear error instead of approximating silently.

## Data

Tournament setup files:

- `data/teams.csv`: `team_id,team_name,group,fifa_rank`
- `data/groups.csv`: `group,team_id`
- `data/initial_elo.csv`: `team_id,elo`
- `data/fifa_r32_slots.csv`: `match_id,slot_a,slot_b`
- `data/fifa_third_place_mapping.csv`: `qualified_third_groups,match_id,third_group`

Attack/Defence model files:

- `data/historical_matches.csv`
- `data/historical_90min_overrides.csv`
- `data/team_attack_defence_ratings.csv`
- `data/model_training_report.json`
- `data/strength_temperature_calibration_report.json`

## Tests

```bash
pytest
```
