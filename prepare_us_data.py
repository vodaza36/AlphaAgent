#!/usr/bin/env python3
"""
Download and update US market data (SP500) through 2026-02-07.

This script downloads only the ~755 SP500 symbols from Yahoo Finance, normalizes them
using Qlib's YahooNormalize1dExtend to maintain continuity with existing data, and
dumps them to Qlib binary format. This is much faster than downloading all 18,145 US symbols.

Estimated time: 10-20 minutes (vs 80+ hours for full US market)

Usage:
    python prepare_us_data.py
"""

import sys
import time
import datetime
from pathlib import Path
from typing import List, Dict
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from loguru import logger
from yahooquery import Ticker
from tqdm import tqdm

# Add qlib scripts to path
qlib_scripts = Path(__file__).parent / "qlib" / "scripts"
sys.path.insert(0, str(qlib_scripts))
sys.path.insert(0, str(qlib_scripts / "data_collector" / "yahoo"))

from dump_bin import DumpDataUpdate
from data_collector.yahoo.collector import YahooNormalizeUS1dExtend
from data_collector.base import Normalize
from qlib.utils import code_to_fname

# Configuration
QLIB_DATA_DIR = Path.home() / ".qlib" / "qlib_data" / "us_data"
INSTRUMENTS_FILE = QLIB_DATA_DIR / "instruments" / "sp500.txt"
TEMP_DIR = Path(__file__).parent / "temp_us_data"
SOURCE_DIR = TEMP_DIR / "source"
NORMALIZE_DIR = TEMP_DIR / "normalize"

# Date range: overlap 1 day with existing data for normalization continuity
START_DATE = "2020-11-09"  # Existing data ends 2020-11-10
END_DATE = "2026-02-07"

# Benchmark indices to include
BENCHMARK_INDICES = ["^GSPC", "^NDX", "^DJI"]

# Batch size for Yahoo queries (max 20 to avoid rate limits)
BATCH_SIZE = 20

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def read_sp500_symbols() -> List[str]:
    """Read SP500 symbols from instruments file."""
    logger.info(f"Reading SP500 symbols from {INSTRUMENTS_FILE}")

    if not INSTRUMENTS_FILE.exists():
        raise FileNotFoundError(
            f"SP500 instruments file not found: {INSTRUMENTS_FILE}\n"
            "Please ensure US data is initialized first."
        )

    symbols = []
    with open(INSTRUMENTS_FILE, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if parts:
                symbols.append(parts[0])

    logger.info(f"Found {len(symbols)} SP500 symbols")
    return symbols


def download_batch(symbols: List[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    """Download data for a batch of symbols using yahooquery."""
    try:
        ticker = Ticker(symbols, asynchronous=False)
        data = ticker.history(start=start, end=end, interval="1d")

        if isinstance(data, pd.DataFrame) and not data.empty:
            # yahooquery returns MultiIndex DataFrame with symbol in index
            result = {}
            if isinstance(data.index, pd.MultiIndex):
                for symbol in symbols:
                    if symbol in data.index.get_level_values(0):
                        df = data.xs(symbol, level=0).reset_index()
                        df["symbol"] = symbol
                        result[symbol] = df
            else:
                # Single symbol case
                data = data.reset_index()
                data["symbol"] = symbols[0]
                result[symbols[0]] = data

            return result

        return {}

    except Exception as e:
        logger.warning(f"Batch download failed for {len(symbols)} symbols: {e}")
        return {}


def download_single(symbol: str, start: str, end: str, retry: int = 0) -> pd.DataFrame:
    """Download data for a single symbol with retry logic."""
    try:
        ticker = Ticker(symbol, asynchronous=False)
        data = ticker.history(start=start, end=end, interval="1d")

        if isinstance(data, pd.DataFrame) and not data.empty:
            if isinstance(data.index, pd.MultiIndex):
                data = data.reset_index()
            else:
                data = data.reset_index()

            data["symbol"] = symbol
            return data

        return pd.DataFrame()

    except Exception as e:
        if retry < MAX_RETRIES:
            logger.debug(f"Retry {retry + 1}/{MAX_RETRIES} for {symbol}")
            time.sleep(RETRY_DELAY)
            return download_single(symbol, start, end, retry + 1)
        else:
            logger.warning(f"Failed to download {symbol} after {MAX_RETRIES} retries: {e}")
            return pd.DataFrame()


def save_to_csv(symbol: str, df: pd.DataFrame, output_dir: Path):
    """Save DataFrame to CSV file with normalized symbol name."""
    if df.empty:
        return

    # Normalize symbol name for filename
    filename = code_to_fname(symbol).upper() + ".csv"
    filepath = output_dir / filename

    # Ensure required columns exist
    required_cols = ["date", "open", "high", "low", "close", "volume", "symbol"]
    for col in required_cols:
        if col not in df.columns:
            logger.warning(f"Missing column {col} for {symbol}")
            return

    # Add adjclose if not present
    if "adjclose" not in df.columns:
        df["adjclose"] = df["close"]

    # IMPORTANT: Ensure date column is formatted as YYYY-MM-DD only (no time/timezone)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Save
    df.to_csv(filepath, index=False)
    logger.debug(f"Saved {symbol} to {filepath}")


def phase_1_build_symbol_list() -> List[str]:
    """Phase 1: Build list of symbols to download (SP500 + benchmarks)."""
    logger.info("=" * 60)
    logger.info("PHASE 1: Building symbol list")
    logger.info("=" * 60)

    sp500_symbols = read_sp500_symbols()
    all_symbols = sp500_symbols + BENCHMARK_INDICES

    logger.info(f"Total symbols to download: {len(all_symbols)}")
    logger.info(f"  - SP500 stocks: {len(sp500_symbols)}")
    logger.info(f"  - Benchmark indices: {len(BENCHMARK_INDICES)}")

    return all_symbols


def phase_2_download_from_yahoo(symbols: List[str]):
    """Phase 2: Download data from Yahoo Finance in batches."""
    logger.info("=" * 60)
    logger.info("PHASE 2: Downloading from Yahoo Finance")
    logger.info("=" * 60)
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Batch size: {BATCH_SIZE} symbols")

    # Create source directory
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    # Download in batches
    num_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
    downloaded = 0
    failed = []

    logger.info(f"Downloading {len(symbols)} symbols in {num_batches} batches...")

    for i in tqdm(range(0, len(symbols), BATCH_SIZE), desc="Downloading batches"):
        batch = symbols[i:i + BATCH_SIZE]
        batch_data = download_batch(batch, START_DATE, END_DATE)

        # Save successful downloads
        for symbol, df in batch_data.items():
            save_to_csv(symbol, df, SOURCE_DIR)
            downloaded += 1

        # Track failed symbols
        failed_in_batch = set(batch) - set(batch_data.keys())
        failed.extend(failed_in_batch)

        # Small delay between batches to avoid rate limiting
        time.sleep(0.5)

    # Retry failed symbols individually
    if failed:
        logger.info(f"Retrying {len(failed)} failed symbols individually...")

        for symbol in tqdm(failed, desc="Retrying failed"):
            df = download_single(symbol, START_DATE, END_DATE)
            if not df.empty:
                save_to_csv(symbol, df, SOURCE_DIR)
                downloaded += 1

            time.sleep(0.5)

    logger.info(f"Download complete: {downloaded}/{len(symbols)} symbols")

    # List CSV files
    csv_files = list(SOURCE_DIR.glob("*.csv"))
    logger.info(f"Created {len(csv_files)} CSV files in {SOURCE_DIR}")


def phase_3_normalize():
    """Phase 3: Normalize data using Qlib's YahooNormalize1dExtend."""
    logger.info("=" * 60)
    logger.info("PHASE 3: Normalizing data")
    logger.info("=" * 60)

    # Create normalize directory
    NORMALIZE_DIR.mkdir(parents=True, exist_ok=True)

    # Use Qlib's normalization with extend mode
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

    import shutil

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
        df = D.features(["AAPL"], ["$close"], start_time="2025-01-01")
        if len(df) > 20:
            logger.info(f"✓ AAPL has {len(df)} records since 2025-01-01")
        else:
            logger.warning(f"✗ AAPL only has {len(df)} records since 2025-01-01")

        # Check benchmark
        df_bench = D.features(["^GSPC"], ["$close"], start_time="2025-01-01")
        if len(df_bench) > 20:
            logger.info(f"✓ ^GSPC has {len(df_bench)} records since 2025-01-01")
        else:
            logger.warning(f"✗ ^GSPC only has {len(df_bench)} records since 2025-01-01")

        logger.info("Verification complete!")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        logger.info("You can verify manually with:")
        logger.info("  python -c \"import qlib; from qlib.data import D; qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us'); print(D.calendar()[-1])\"")


def main():
    """Main execution flow."""
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("US Market Data Downloader")
    logger.info("=" * 60)
    logger.info(f"Target date range: {START_DATE} to {END_DATE}")
    logger.info(f"Qlib data directory: {QLIB_DATA_DIR}")
    logger.info("")

    try:
        # Phase 1: Build symbol list
        symbols = phase_1_build_symbol_list()

        # Phase 2: Download from Yahoo
        phase_2_download_from_yahoo(symbols)

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
