from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR
from src.model_calibration import (
    CalibrationConfig,
    calibrate_strength_temperature_and_regularization,
    write_calibration_outputs,
)


def parse_float_grid(value: str) -> tuple[float, ...]:
    try:
        parsed = tuple(float(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Grid values must be comma-separated numbers") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("Grid must contain at least one value")
    if any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("Grid values must be positive")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate Attack/Defence regularization alpha and strength temperature.")
    parser.add_argument("--matches", default=str(DATA_DIR / "historical_matches.csv"))
    parser.add_argument("--output-report", default=str(DATA_DIR / "strength_temperature_calibration_report.json"))
    parser.add_argument("--output-grid", default=None)
    parser.add_argument("--train-start-date", default="2022-01-01")
    parser.add_argument("--train-end-date", default="2024-12-31")
    parser.add_argument("--test-start-date", default="2025-01-01")
    parser.add_argument("--test-end-date", default=None)
    parser.add_argument("--half-life-grid", type=parse_float_grid, default=(180.0, 365.0, 500.0, 730.0))
    parser.add_argument("--min-matches-per-team", type=int, default=15)
    parser.add_argument("--regularization-grid", type=parse_float_grid, default=(0.001, 0.01, 0.05, 0.1))
    parser.add_argument("--gamma-grid", type=parse_float_grid, default=(0.8, 0.9, 1.0))
    parser.add_argument("--rolling-backtest", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    matches = pd.read_csv(args.matches)
    config = CalibrationConfig(
        train_start_date=args.train_start_date,
        train_end_date=args.train_end_date,
        test_start_date=args.test_start_date,
        test_end_date=args.test_end_date,
        half_life_grid=args.half_life_grid,
        min_matches_per_team=args.min_matches_per_team,
        regularization_grid=args.regularization_grid,
        gamma_grid=args.gamma_grid,
        rolling_backtest=args.rolling_backtest,
    )
    result = calibrate_strength_temperature_and_regularization(matches, config)
    write_calibration_outputs(result, Path(args.output_report), Path(args.output_grid) if args.output_grid else None)
    print(
        "Calibration complete: "
        f"best half-life={result.report['best_half_life_days']}, "
        f"best alpha={result.report['best_regularization_alpha']}, "
        f"best gamma={result.report['best_strength_temperature']}, "
        f"rolling NLL={result.report['rolling_total_nll']:.3f}, "
        f"main holdout NLL={result.report['main_holdout_nll']:.3f}"
    )


if __name__ == "__main__":
    main()
