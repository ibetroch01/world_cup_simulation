# FIFA World Cup 2026 Simulator

Python + Streamlit Monte Carlo dashboard for the 48-team FIFA World Cup 2026 format.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Model Assumptions

- This is Monte Carlo simulation, not MCMC.
- Elo is fixed unless `Update Elo during tournament` is enabled.
- Goals are generated from a Poisson model with fixed total expected goals and Elo-based goal share.
- Draws arise naturally from equal Poisson scores.
- Knockout draws after 90 minutes are resolved by Elo-weighted advancement.
- Dynamic Elo updates, when enabled, use only the 90-minute result, not the penalty winner.
- Fair play is represented as a deterministic placeholder score of zero.
- Annex C third-place mapping is required for exact bracket loading. If the mapping CSV is incomplete or invalid, the simulator raises a clear error instead of approximating silently.

## Data

The app expects:

- `data/teams.csv`: `team_id,team_name,group,fifa_rank`
- `data/groups.csv`: `group,team_id`
- `data/initial_elo.csv`: `team_id,elo`
- `data/fifa_r32_slots.csv`: `match_id,slot_a,slot_b`
- `data/fifa_third_place_mapping.csv`: `qualified_third_groups,match_id,third_group`

`data/fifa_third_place_mapping.csv` contains 495 qualifying third-place combinations and eight match assignments per combination. The table was transcribed from Annexe C of FIFA's May 2026 `FWC2026_regulations_EN.pdf`, with the public knockout-stage table used as a parsing cross-check.

## Tests

```bash
pytest
```
