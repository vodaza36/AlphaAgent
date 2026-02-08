#!/usr/bin/env python3
"""Complete the US data update (normalization, dump, cleanup, verification)."""

import sys
import time
import shutil
from pathlib import Path
import multiprocessing

from loguru import logger
import pandas as pd

# Add qlib scripts to path
qlib_scripts = Path(__file__).parent / "qlib" / "scripts"
sys.path.insert(0, str(qlib_scripts))
sys.path.insert(0, str(qlib_scripts / "data_collector" / "yahoo"))

from dump_bin import DumpDataUpdate
from data_collector.yahoo.collector import YahooNormalizeUS1dExtend
from data_collector.base import Normalize

# Configuration
QLIB_DATA_DIR = Path.home() / ".qlib" / "qlib_data" / "us_data"
TEMP_DIR = Path(__file__).parent / "temp_us_data"
SOURCE_DIR = TEMP_DIR / "source"
NORMALIZE_DIR = TEMP_DIR / "normalize"


def phase_3_normalize():
    """Phase 3: Normalize data using Qlib's YahooNormalizeUS1dExtend."""
    logger.info("=" * 60)
    logger.info("PHASE 3: Normalizing data")
    logger.info("=" * 60)

    # Create normalize directory
    NORMALIZE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Using YahooNormalizeUS1dExtend to maintain data continuity...")

    normalizer = Normalize(
        source_dir=str(SOURCE_DIR),
        target_dir=str(NORMALIZE_DIR),
        normalize_class=YahooNormalizeUS1dExtend,
        max_workers=8,
        date_field_name="date",
        symbol_field_name="symbol",
        old_qlib_data_dir=str(QLIB_DATA_DIR),
    )

    normalizer.normalize()

    # List normalized files
    csv_files = list(NORMALIZE_DIR.glob("*.csv"))
    logger.info(f"Normalized {len(csv_files)} files in {NORMALIZE_DIR}")


def phase_4_dump_to_binary():
    """Phase 4: Convert to Qlib binary format using DumpDataUpdate."""
    logger.info("=" * 60)
    logger.info("PHASE 4: Dumping to binary format")
    logger.info("=" * 60)

    logger.info(f"Updating Qlib data directory: {QLIB_DATA_DIR}")

    # Determine number of workers
    max_workers = max(multiprocessing.cpu_count() - 2, 1)

    dumper = DumpDataUpdate(
        data_path=str(NORMALIZE_DIR),
        qlib_dir=str(QLIB_DATA_DIR),
        exclude_fields="symbol,date",
        max_workers=max_workers,
        freq="day",
        date_field_name="date",
        symbol_field_name="symbol",
    )

    logger.info("Dumping data (this may take a few minutes)...")
    dumper.dump()

    logger.info("Binary dump complete!")


def cleanup_temp_files():
    """Remove temporary directories."""
    logger.info("=" * 60)
    logger.info("Cleaning up temporary files")
    logger.info("=" * 60)

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        logger.info(f"Removed temporary directory: {TEMP_DIR}")


def verify_update():
    """Verify that the update was successful."""
    logger.info("=" * 60)
    logger.info("Verifying update")
    logger.info("=" * 60)

    try:
        import qlib
        from qlib.data import D

        qlib.init(provider_uri=str(QLIB_DATA_DIR), region="us")

        # Check calendar
        cal = D.calendar()
        logger.info(f"Calendar date range: {cal[0]} to {cal[-1]}")

        if cal[-1] >= pd.Timestamp("2026-02-06"):
            logger.info("✓ Calendar extends to 2026")
        else:
            logger.warning(f"✗ Calendar only extends to {cal[-1]}")

        # Check sample data for AAPL
        try:
            df = D.features(["AAPL"], ["$close"], start_time="2025-01-01")
            if len(df) > 20:
                logger.info(f"✓ AAPL has {len(df)} records since 2025-01-01")
            else:
                logger.warning(f"✗ AAPL only has {len(df)} records since 2025-01-01")
        except Exception as e:
            logger.warning(f"Could not verify AAPL data: {e}")

        # Check benchmark
        try:
            df_bench = D.features(["^GSPC"], ["$close"], start_time="2025-01-01")
            if len(df_bench) > 20:
                logger.info(f"✓ ^GSPC has {len(df_bench)} records since 2025-01-01")
            else:
                logger.warning(f"✗ ^GSPC only has {len(df_bench)} records since 2025-01-01")
        except Exception as e:
            logger.warning(f"Could not verify ^GSPC data: {e}")

        logger.info("Verification complete!")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        logger.info("You can verify manually with:")
        logger.info("  python -c \"import qlib; from qlib.data import D; qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us'); print(D.calendar()[-1])\"")


def main():
    """Main execution flow."""
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("US Market Data Update - Final Phases")
    logger.info("=" * 60)

    try:
        # Phase 3: Normalize
        phase_3_normalize()

        # Phase 4: Dump to binary
        phase_4_dump_to_binary()

        # Cleanup
        cleanup_temp_files()

        # Verify
        verify_update()

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"SUCCESS! Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        logger.info("=" * 60)

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
