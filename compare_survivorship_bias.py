#!/usr/bin/env python3
"""
Compare old vs new dataset to demonstrate survivorship bias impact.

This script analyzes the differences between a survivorship-biased dataset
and the survivorship-bias-free dataset to quantify the bias effect.

Usage:
    # If you have backup of old data:
    python compare_survivorship_bias.py --old-data ~/.qlib/qlib_data/us_data_backup --new-data ~/.qlib/qlib_data/us_data

    # Or just analyze new data:
    python compare_survivorship_bias.py --new-data ~/.qlib/qlib_data/us_data
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime

# Add qlib to path
qlib_path = Path(__file__).parent / "qlib"
sys.path.insert(0, str(qlib_path))

import qlib
from qlib.data import D


def parse_instruments_file(instruments_file: Path) -> Dict[str, Tuple[str, str]]:
    """Parse instruments file and return dict of symbol -> (start_date, end_date)."""
    instruments = {}

    with open(instruments_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                symbol, start_date, end_date = parts[0], parts[1], parts[2]
                instruments[symbol] = (start_date, end_date)
            elif len(parts) == 1:
                # Old format: just symbol
                symbol = parts[0]
                instruments[symbol] = ('1990-01-01', '2099-12-31')

    return instruments


def analyze_instruments(instruments_file: Path, label: str):
    """Analyze instruments file and report statistics."""
    logger.info("=" * 60)
    logger.info(f"Analyzing {label}")
    logger.info("=" * 60)

    if not instruments_file.exists():
        logger.error(f"Instruments file not found: {instruments_file}")
        return None

    instruments = parse_instruments_file(instruments_file)

    # Categorize stocks
    total = len(instruments)
    benchmarks = [sym for sym in instruments if sym.startswith('^')]
    stocks = [sym for sym in instruments if not sym.startswith('^')]

    active = [sym for sym, (start, end) in instruments.items()
              if end == '2099-12-31' and not sym.startswith('^')]
    delisted = [sym for sym, (start, end) in instruments.items()
                if end != '2099-12-31' and not sym.startswith('^')]

    # Analyze delisting dates
    delisted_2020_2026 = []
    delisted_before_2020 = []

    for sym in delisted:
        _, end_date = instruments[sym]
        end_year = int(end_date.split('-')[0])

        if 2020 <= end_year <= 2026:
            delisted_2020_2026.append((sym, end_date))
        elif end_year < 2020:
            delisted_before_2020.append((sym, end_date))

    logger.info(f"Total instruments: {total}")
    logger.info(f"  - Stocks: {len(stocks)}")
    logger.info(f"  - Benchmarks: {len(benchmarks)}")
    logger.info(f"")
    logger.info(f"Stock breakdown:")
    logger.info(f"  - Active (end = 2099-12-31): {len(active)}")
    logger.info(f"  - Delisted: {len(delisted)}")
    logger.info(f"")
    logger.info(f"Delisting timeline:")
    logger.info(f"  - Before 2020: {len(delisted_before_2020)}")
    logger.info(f"  - 2020-2026: {len(delisted_2020_2026)}")

    if len(delisted_2020_2026) == 0 and len(delisted) > 0:
        logger.warning("⚠️  SURVIVORSHIP BIAS DETECTED!")
        logger.warning(f"   All {len(delisted)} delistings are before 2020")
        logger.warning("   Missing ~50-100+ delistings from 2020-2026 period")

    if len(delisted_2020_2026) > 0:
        logger.info(f"")
        logger.info(f"Example delistings (2020-2026):")
        for sym, end_date in sorted(delisted_2020_2026, key=lambda x: x[1])[:10]:
            logger.info(f"  - {sym}: delisted {end_date}")

    return {
        'total': total,
        'stocks': len(stocks),
        'benchmarks': len(benchmarks),
        'active': len(active),
        'delisted': len(delisted),
        'delisted_2020_2026': len(delisted_2020_2026),
        'delisted_before_2020': len(delisted_before_2020),
        'instruments': instruments,
        'delisted_2020_2026_list': delisted_2020_2026,
    }


def compare_datasets(old_data: Dict, new_data: Dict):
    """Compare old and new datasets."""
    logger.info("=" * 60)
    logger.info("Comparison: Old vs New Dataset")
    logger.info("=" * 60)

    # Compare totals
    logger.info(f"Total instruments:")
    logger.info(f"  Old: {old_data['total']}")
    logger.info(f"  New: {new_data['total']}")
    logger.info(f"  Difference: {new_data['total'] - old_data['total']:+d}")
    logger.info("")

    # Compare active stocks
    logger.info(f"Active stocks:")
    logger.info(f"  Old: {old_data['active']}")
    logger.info(f"  New: {new_data['active']}")
    logger.info(f"  Difference: {new_data['active'] - old_data['active']:+d}")
    logger.info("")

    # Compare delistings
    logger.info(f"Delisted stocks (2020-2026):")
    logger.info(f"  Old: {old_data['delisted_2020_2026']}")
    logger.info(f"  New: {new_data['delisted_2020_2026']}")
    logger.info(f"  Difference: {new_data['delisted_2020_2026'] - old_data['delisted_2020_2026']:+d}")

    if new_data['delisted_2020_2026'] > old_data['delisted_2020_2026']:
        logger.info(f"  ✓ New dataset includes {new_data['delisted_2020_2026'] - old_data['delisted_2020_2026']} additional delistings")
    logger.info("")

    # Find new delistings
    old_instruments = set(old_data['instruments'].keys())
    new_instruments = set(new_data['instruments'].keys())

    new_delistings = new_instruments - old_instruments
    removed_symbols = old_instruments - new_instruments

    if new_delistings:
        logger.info(f"New symbols in updated dataset: {len(new_delistings)}")
        logger.info("Examples:")
        for sym in list(new_delistings)[:10]:
            start, end = new_data['instruments'][sym]
            logger.info(f"  - {sym}: {start} to {end}")
        logger.info("")

    if removed_symbols:
        logger.info(f"Symbols removed in updated dataset: {len(removed_symbols)}")
        logger.info("Examples:")
        for sym in list(removed_symbols)[:10]:
            start, end = old_data['instruments'][sym]
            logger.info(f"  - {sym}: {start} to {end}")
        logger.info("")

    # Survivorship bias impact
    if old_data['delisted_2020_2026'] == 0 and new_data['delisted_2020_2026'] > 0:
        logger.info("=" * 60)
        logger.info("SURVIVORSHIP BIAS IMPACT")
        logger.info("=" * 60)
        logger.info(f"The old dataset had ZERO delistings from 2020-2026.")
        logger.info(f"The new dataset includes {new_data['delisted_2020_2026']} delistings.")
        logger.info("")
        logger.info("Expected backtest impact:")
        logger.info("  - Old dataset: Tests only survivors (optimistically biased)")
        logger.info("  - New dataset: Tests all stocks at each point in time (realistic)")
        logger.info("  - Expected performance drop: 10-30% (typical survivorship bias)")
        logger.info("")
        logger.info("Example: If old dataset showed Sharpe=1.8, expect Sharpe~1.4-1.5 with new dataset")


def check_vwap_availability(data_dir: Path, label: str):
    """Check if VWAP field is available."""
    logger.info("=" * 60)
    logger.info(f"VWAP Availability Check: {label}")
    logger.info("=" * 60)

    features_dir = data_dir / "features"
    if not features_dir.exists():
        logger.error(f"Features directory not found: {features_dir}")
        return False

    # Check for VWAP files
    vwap_files = list(features_dir.glob("*/vwap.day.bin"))
    stock_dirs = [d for d in features_dir.iterdir() if d.is_dir()]

    logger.info(f"Total stock directories: {len(stock_dirs)}")
    logger.info(f"VWAP files found: {len(vwap_files)}")

    if len(vwap_files) == 0:
        logger.error("✗ No VWAP files found - Alpha158 will have NaN features")
        return False
    elif len(vwap_files) < len(stock_dirs) * 0.9:
        logger.warning(f"⚠ Only {len(vwap_files)}/{len(stock_dirs)} stocks have VWAP")
        return False
    else:
        logger.info(f"✓ VWAP available for {len(vwap_files)}/{len(stock_dirs)} stocks")
        return True


def simulate_backtest_impact(old_data: Dict, new_data: Dict):
    """Simulate the impact of survivorship bias on backtest results."""
    logger.info("=" * 60)
    logger.info("Simulated Backtest Impact")
    logger.info("=" * 60)

    if old_data['delisted_2020_2026'] == 0:
        bias_pct = new_data['delisted_2020_2026'] / (new_data['active'] + new_data['delisted_2020_2026']) * 100

        logger.info(f"Survivorship bias rate: {bias_pct:.1f}%")
        logger.info(f"  ({new_data['delisted_2020_2026']} delisted / {new_data['active'] + new_data['delisted_2020_2026']} total)")
        logger.info("")

        # Estimate impact
        # Typical survivorship bias inflates returns by 1.5-3x the bias rate
        estimated_return_inflation = bias_pct * 2.0
        estimated_sharpe_inflation = bias_pct * 1.5

        logger.info("Estimated performance inflation in old dataset:")
        logger.info(f"  - Annual returns: +{estimated_return_inflation:.1f} percentage points")
        logger.info(f"  - Sharpe ratio: +{estimated_sharpe_inflation/100:.2f} points")
        logger.info("")

        logger.info("Example scenarios:")
        logger.info("  Scenario 1: Momentum factor")
        logger.info("    - Old dataset: Sharpe=1.80, Return=18.0%")
        logger.info(f"    - New dataset (est): Sharpe={1.80 - estimated_sharpe_inflation/100:.2f}, Return={18.0 - estimated_return_inflation:.1f}%")
        logger.info("")
        logger.info("  Scenario 2: Mean reversion factor")
        logger.info("    - Old dataset: Sharpe=1.20, Return=12.0%")
        logger.info(f"    - New dataset (est): Sharpe={1.20 - estimated_sharpe_inflation/100:.2f}, Return={12.0 - estimated_return_inflation:.1f}%")
        logger.info("")

        logger.info("NOTE: These are rough estimates. Actual impact depends on factor type.")
        logger.info("      Momentum factors typically have higher survivorship bias.")
        logger.info("      Mean reversion factors typically have lower survivorship bias.")


def main():
    """Main execution flow."""
    parser = argparse.ArgumentParser(
        description='Compare old and new datasets to demonstrate survivorship bias impact'
    )
    parser.add_argument(
        '--old-data',
        type=str,
        help='Path to old dataset (default: ~/.qlib/qlib_data/us_data_backup)'
    )
    parser.add_argument(
        '--new-data',
        type=str,
        default=str(Path.home() / ".qlib" / "qlib_data" / "us_data"),
        help='Path to new dataset (default: ~/.qlib/qlib_data/us_data)'
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Survivorship Bias Comparison Tool")
    logger.info("=" * 60)
    logger.info("")

    # Analyze new dataset
    new_data_path = Path(args.new_data)
    new_instruments_file = new_data_path / "instruments" / "sp500.txt"

    new_data = analyze_instruments(new_instruments_file, "New Dataset")
    logger.info("")

    # Check VWAP
    has_vwap = check_vwap_availability(new_data_path, "New Dataset")
    logger.info("")

    # Analyze old dataset if provided
    if args.old_data:
        old_data_path = Path(args.old_data)
        old_instruments_file = old_data_path / "instruments" / "sp500.txt"

        if old_instruments_file.exists():
            old_data = analyze_instruments(old_instruments_file, "Old Dataset")
            logger.info("")

            # Compare
            compare_datasets(old_data, new_data)
            logger.info("")

            # Check VWAP in old dataset
            old_has_vwap = check_vwap_availability(old_data_path, "Old Dataset")
            logger.info("")

            if not old_has_vwap and has_vwap:
                logger.info("=" * 60)
                logger.info("VWAP IMPROVEMENT")
                logger.info("=" * 60)
                logger.info("✓ New dataset includes VWAP field (old dataset did not)")
                logger.info("  - Old dataset: Alpha158 had NaN features for VWAP indicators")
                logger.info("  - New dataset: Full 158 features available")
                logger.info("")

            # Simulate backtest impact
            simulate_backtest_impact(old_data, new_data)
        else:
            logger.error(f"Old dataset not found: {old_instruments_file}")
            logger.info("Run with just --new-data to analyze the new dataset only")
    else:
        logger.info("=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info("Run with --old-data to compare against a backup dataset")
        logger.info(f"Example: python {sys.argv[0]} --old-data ~/.qlib/qlib_data/us_data_backup --new-data {args.new_data}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("Analysis Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
