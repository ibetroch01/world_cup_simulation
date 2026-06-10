from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR
from src.data_sources import (
    HistoricalSourceConfig,
    build_historical_matches_dataset,
    write_historical_matches,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a validated historical international match dataset.")
    parser.add_argument("--start-date", default="2022-01-01")
    parser.add_argument("--end-date", default=None, help="Inclusive YYYY-MM-DD end date. Defaults to today.")
    parser.add_argument("--output", default=str(DATA_DIR / "historical_matches.csv"))
    parser.add_argument("--manual-input", default=None, help="Optional manually maintained CSV with required columns.")
    parser.add_argument(
        "--overrides",
        default=str(DATA_DIR / "historical_90min_overrides.csv"),
        help="CSV containing known extra-time score corrections to 90-minute scores.",
    )
    parser.add_argument(
        "--allow-missing-overrides",
        action="store_true",
        help="Allow override rows that are not present in the selected source/date window.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = HistoricalSourceConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        overrides_path=Path(args.overrides) if args.overrides else None,
        manual_input_path=Path(args.manual_input) if args.manual_input else None,
        allow_missing_overrides=bool(args.allow_missing_overrides),
    )
    matches = build_historical_matches_dataset(config)
    write_historical_matches(matches, Path(args.output))
    print(f"Wrote {len(matches):,} historical matches to {args.output}")


if __name__ == "__main__":
    main()
