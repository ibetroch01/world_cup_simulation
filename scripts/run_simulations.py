from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.attack_defence_model import load_attack_defence_model
from src.config import DATA_DIR, SimulationConfig
from src.data_loader import load_all_data
from src.locked_matches import empty_locked_match_index, load_locked_matches
from src.simulation import run_standard_simulations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Attack/Defence World Cup 2026 simulations.")
    parser.add_argument("--runs", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ratings-file", default=str(DATA_DIR / "team_attack_defence_ratings.csv"))
    parser.add_argument("--training-report", default=str(DATA_DIR / "model_training_report.json"))
    parser.add_argument("--penalty-damping", type=float, default=900.0)
    parser.add_argument("--goals-scale", type=float, default=1.0)
    parser.add_argument("--strength-temperature", type=float, default=0.8)
    parser.add_argument("--live-early-prediction", action="store_true")
    parser.add_argument("--locked-matches", default=str(DATA_DIR / "locked_matches.csv"))
    return parser.parse_args()


def metadata_path(value: str) -> str:
    path = Path(value)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return value


def main() -> None:
    args = parse_args()
    teams, elos, slots, mapping = load_all_data()
    team_names = dict(zip(teams["team_id"], teams["team_name"]))
    attack_defence = load_attack_defence_model(
        Path(args.ratings_file),
        Path(args.training_report),
        goals_scale=args.goals_scale,
        strength_temperature=args.strength_temperature,
    )

    def goal_model(team_a: str, team_b: str) -> tuple[float, float]:
        return attack_defence.expected_goals(team_names.get(team_a, team_a), team_names.get(team_b, team_b))

    locked_matches = (
        load_locked_matches(Path(args.locked_matches), teams)
        if args.live_early_prediction
        else empty_locked_match_index()
    )

    team_ratings_rows = []
    for row in teams.sort_values(["group", "team_name"]).itertuples(index=False):
        team_name = str(row.team_name)
        rating = attack_defence.ratings.get(team_name)
        rating_source = "trained"
        if rating is None:
            rating = attack_defence.rating_for(team_name)
            rating_source = "fallback"
        team_ratings_rows.append(
            {
                "team": team_name,
                "team_id": row.team_id,
                "group": row.group,
                "attack_score": rating.attack_score,
                "defence_score": rating.defence_score,
                "overall_score": rating.overall_score,
                "matches_used": rating.matches_used,
                "rating_source": rating_source,
            }
        )

    config = SimulationConfig(penalty_damping=args.penalty_damping, random_seed=args.seed)
    group_df, knockout_df, diagnostics = run_standard_simulations(
        args.runs,
        teams,
        elos,
        slots,
        mapping,
        config,
        goal_model=goal_model,
        locked_matches=locked_matches if args.live_early_prediction else None,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model": "attack_defence",
        "runs": args.runs,
        "seed": args.seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "ratings_file": metadata_path(args.ratings_file),
            "training_report": metadata_path(args.training_report),
            "base_rate": attack_defence.base_rate,
            "goals_scale": args.goals_scale,
            "strength_temperature": args.strength_temperature,
            "penalty_damping": args.penalty_damping,
            "live_early_prediction": args.live_early_prediction,
            "locked_matches_file": metadata_path(args.locked_matches) if args.live_early_prediction else None,
            "locked_matches_count": locked_matches.count if args.live_early_prediction else 0,
            "latest_locked_match_at": locked_matches.latest_played_at if args.live_early_prediction else None,
        },
        "live_early_prediction": args.live_early_prediction,
        "locked_matches_file": metadata_path(args.locked_matches) if args.live_early_prediction else None,
        "locked_matches_count": locked_matches.count if args.live_early_prediction else 0,
        "latest_locked_match_at": locked_matches.latest_played_at if args.live_early_prediction else None,
        "ratings_file": "team_ratings.csv",
        "diagnostics": diagnostics,
    }
    group_df.to_csv(output_dir / "group_phase_results.csv", index=False)
    knockout_df.to_csv(output_dir / "knockout_phase_results.csv", index=False)
    pd.DataFrame(team_ratings_rows).to_csv(output_dir / "team_ratings.csv", index=False)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote simulation outputs to {output_dir}")


if __name__ == "__main__":
    main()
