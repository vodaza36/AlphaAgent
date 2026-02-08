#!/usr/bin/env python3
"""
Complete the US data build from where prepare_us_data_v2.py failed.

This script:
1. Uses the downloaded source files directly (skips problematic normalization)
2. Dumps to Qlib binary format
3. Rebuilds instruments file

Usage:
    python complete_us_data_build.py
"""

import sys
import time
import multiprocessing
from pathlib import Path

from loguru import logger

# Add qlib scripts to path
qlib_scripts = Path(__file__).parent / "qlib" / "scripts"
sys.path.insert(0, str(qlib_scripts))

from dump_bin import DumpDataAll

# Configuration
QLIB_DATA_DIR = Path.home() / ".qlib" / "qlib_data" / "us_data"
SOURCE_DIR = Path(__file__).parent / "temp_us_data_v2" / "source"
INSTRUMENTS_FILE = QLIB_DATA_DIR / "instruments" / "sp500.txt"

# Benchmark indices
BENCHMARK_INDICES = ["^GSPC", "^NDX", "^DJI"]


def rebuild_instruments_from_source():
    """Rebuild instruments file from source CSV files."""
    logger.info("=" * 60)
    logger.info("Rebuild Instruments File from Source")
    logger.info("=" * 60)

    import pandas as pd

    # Get all source CSV files
    csv_files = list(SOURCE_DIR.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} source CSV files")

    symbol_dates = {}

    for csv_file in csv_files:
        symbol = csv_file.stem.upper()

        try:
            df = pd.read_csv(csv_file)
            if len(df) > 0:
                start_date = df['date'].min()
                end_date = df['date'].max()

                # For now, assume all stocks are active unless they end before 2026
                if pd.to_datetime(end_date) < pd.Timestamp('2026-01-01'):
                    symbol_dates[symbol] = (start_date, end_date)
                else:
                    symbol_dates[symbol] = (start_date, '2099-12-31')

        except Exception as e:
            logger.warning(f"Could not process {csv_file}: {e}")

    # Write instruments file
    instruments_dir = QLIB_DATA_DIR / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)

    sorted_symbols = sorted(symbol_dates.keys())

    with open(INSTRUMENTS_FILE, 'w') as f:
        for symbol in sorted_symbols:
            start_date, end_date = symbol_dates[symbol]
            f.write(f"{symbol}\t{start_date}\t{end_date}\n")

    logger.info(f"Wrote {len(sorted_symbols)} symbols to {INSTRUMENTS_FILE}")

    # Count active vs delisted
    active = sum(1 for _, end in symbol_dates.values() if end == '2099-12-31')
    delisted = len(sorted_symbols) - active

    logger.info(f"  - Active stocks: {active}")
    logger.info(f"  - Delisted stocks: {delisted}")


def dump_to_binary():
    """Dump source CSV files to Qlib binary format."""
    logger.info("=" * 60)
    logger.info("Dump to Binary Format")
    logger.info("=" * 60)

    logger.info(f"Source directory: {SOURCE_DIR}")
    logger.info(f"Target Qlib directory: {QLIB_DATA_DIR}")

    # Determine number of workers
    max_workers = max(multiprocessing.cpu_count() - 2, 1)

    dumper = DumpDataAll(
        data_path=str(SOURCE_DIR),
        qlib_dir=str(QLIB_DATA_DIR),
        include_fields="open,high,low,close,volume,adjclose,vwap",
        exclude_fields="symbol,date",
        max_workers=max_workers,
        freq="day",
        date_field_name="date",
        symbol_field_name="symbol",
    )

    logger.info("Dumping data (this may take 5-10 minutes)...")
    dumper.dump()

    logger.info("Binary dump complete!")


def verify():
    """Verify the dataset."""
    logger.info("=" * 60)
    logger.info("Verify Dataset")
    logger.info("=" * 60)

    try:
        import qlib
        from qlib.data import D
        import pandas as pd

        qlib.init(provider_uri=str(QLIB_DATA_DIR), region="us")

        # Check calendar
        cal = D.calendar()
        logger.info(f"Calendar date range: {cal[0]} to {cal[-1]}")

        if cal[-1] >= pd.Timestamp("2026-02-06"):
            logger.info("✓ Calendar extends to 2026")
        else:
            logger.warning(f"✗ Calendar only extends to {cal[-1]}")

        # Check instruments
        instruments = D.instruments('sp500')
        logger.info(f"Total instruments: {len(instruments)}")

        # Check VWAP field for AAPL
        try:
            df = D.features(["AAPL"], ["$close", "$vwap"], start_time="2025-01-01")
            if len(df) > 20 and df['$vwap'].notna().sum() > 20:
                logger.info(f"✓ AAPL has {len(df)} records with VWAP since 2025-01-01")
            else:
                logger.warning(f"✗ AAPL has insufficient VWAP data")
        except Exception as e:
            logger.error(f"✗ Failed to read VWAP for AAPL: {e}")

        # Check that vwap.day.bin files exist
        vwap_files = list((QLIB_DATA_DIR / "features").glob("*/vwap.day.bin"))
        logger.info(f"✓ Found {len(vwap_files)} vwap.day.bin files")

        logger.info("Verification complete!")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main execution."""
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("Complete US Data V2 Build")
    logger.info("=" * 60)
    logger.info(f"Source directory: {SOURCE_DIR}")
    logger.info(f"Qlib data directory: {QLIB_DATA_DIR}")
    logger.info("")

    try:
        # Rebuild instruments from source
        rebuild_instruments_from_source()

        # Dump to binary
        dump_to_binary()

        # Verify
        verify()

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"SUCCESS! Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Clear caches: rm -rf ./git_ignore_folder ./pickle_cache")
        logger.info("2. Test Alpha158: python test_alpha158_vwap.py")
        logger.info("3. Run backtests with the new dataset")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
