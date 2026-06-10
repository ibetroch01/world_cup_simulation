from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR
from src.model_training import TrainingConfig, train_from_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Attack/Defence ratings from historical match data.")
    parser.add_argument("--matches", default=str(DATA_DIR / "historical_matches.csv"))
    parser.add_argument("--output-ratings", default=str(DATA_DIR / "team_attack_defence_ratings.csv"))
    parser.add_argument("--output-report", default=str(DATA_DIR / "model_training_report.json"))
    parser.add_argument("--start-date", default="2022-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--half-life-days", type=float, default=730.0)
    parser.add_argument("--regularization-alpha", type=float, default=0.01)
    parser.add_argument("--min-matches-per-team", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TrainingConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        half_life_days=args.half_life_days,
        regularization_alpha=args.regularization_alpha,
        min_matches_per_team=args.min_matches_per_team,
    )
    result = train_from_csv(Path(args.matches), Path(args.output_ratings), Path(args.output_report), config)
    print(
        "Trained Attack/Defence model on "
        f"{result.report['n_matches']:,} matches; ratings written to {args.output_ratings}"
    )


if __name__ == "__main__":
    main()
