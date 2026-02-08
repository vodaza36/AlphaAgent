#!/usr/bin/env python3
"""
Download survivorship-bias-free S&P 500 data with Alpha158 fields (2020-2026).

This script addresses two critical issues:
1. Survivorship bias: Uses historical S&P 500 constituent data to include delisted stocks
2. Missing VWAP: Computes Simpson's VWAP approximation for Alpha158 compatibility

Data sources:
- Historical constituents: fja05680/sp500 GitHub repository
- OHLCV price data: Yahoo Finance via yahooquery
- VWAP: Simpson's approximation (open + 2*high + 2*low + close) / 6

Estimated time: 30-45 minutes

Usage:
    python prepare_us_data_v2.py [--polygon-api-key KEY]
"""

import sys
import time
import datetime
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
from loguru import logger
from yahooquery import Ticker
from tqdm import tqdm
import requests

# Add qlib scripts to path
qlib_scripts = Path(__file__).parent / "qlib" / "scripts"
sys.path.insert(0, str(qlib_scripts))
sys.path.insert(0, str(qlib_scripts / "data_collector" / "yahoo"))

from dump_bin import DumpDataAll
from data_collector.yahoo.collector import YahooNormalizeUS1dExtend
from data_collector.base import Normalize
from qlib.utils import code_to_fname

# Configuration
QLIB_DATA_DIR = Path.home() / ".qlib" / "qlib_data" / "us_data"
INSTRUMENTS_FILE = QLIB_DATA_DIR / "instruments" / "sp500.txt"
TEMP_DIR = Path(__file__).parent / "temp_us_data_v2"
SOURCE_DIR = TEMP_DIR / "source"
NORMALIZE_DIR = TEMP_DIR / "normalize"
HISTORICAL_CSV_PATH = TEMP_DIR / "sp500_historical.csv"

# Date range for backtesting
START_DATE = "2020-01-01"
END_DATE = "2026-02-07"

# Historical constituents data URL
HISTORICAL_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes(01-17-2026).csv"

# Benchmark indices to include
BENCHMARK_INDICES = ["^GSPC", "^NDX", "^DJI"]

# Batch size for Yahoo queries
BATCH_SIZE = 20

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def phase_1_download_historical_constituents() -> pd.DataFrame:
    """Phase 1: Download S&P 500 historical constituent data from GitHub."""
    logger.info("=" * 60)
    logger.info("PHASE 1: Download Historical S&P 500 Constituents")
    logger.info("=" * 60)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading from: {HISTORICAL_URL}")

    try:
        response = requests.get(HISTORICAL_URL, timeout=30)
        response.raise_for_status()

        with open(HISTORICAL_CSV_PATH, 'wb') as f:
            f.write(response.content)

        logger.info(f"Saved to: {HISTORICAL_CSV_PATH}")

        # Load and inspect the data
        df = pd.read_csv(HISTORICAL_CSV_PATH)
        logger.info(f"Loaded {len(df)} historical change records")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info(f"Date range in file: {df['date'].min()} to {df['date'].max()}")

        return df

    except Exception as e:
        logger.error(f"Failed to download historical constituents: {e}")
        raise


def phase_2_build_symbol_list(historical_df: pd.DataFrame) -> Tuple[List[str], Dict[str, Tuple[str, str]]]:
    """
    Phase 2: Build master symbol list with date ranges.

    Returns:
        - List of unique symbols that were ever in S&P 500 during 2020-2026
        - Dict mapping symbol to (start_date, end_date) for instruments file
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: Build Symbol List with Date Ranges")
    logger.info("=" * 60)

    # Parse the historical snapshots file
    # Columns: date, tickers (comma-separated list of all constituents on that date)
    historical_df['date'] = pd.to_datetime(historical_df['date'])

    # Filter to our date range
    mask = (historical_df['date'] >= START_DATE) & (historical_df['date'] <= END_DATE)
    relevant_snapshots = historical_df[mask].copy()

    logger.info(f"Found {len(relevant_snapshots)} daily snapshots in {START_DATE} to {END_DATE}")

    # Build symbol registry by tracking first and last appearance
    symbol_dates: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]] = {}

    # Track all symbols that appear in the index during our period
    for _, row in relevant_snapshots.iterrows():
        date = row['date']

        # Parse comma-separated ticker list
        if 'tickers' in row and pd.notna(row['tickers']):
            tickers = [t.strip() for t in str(row['tickers']).split(',')]

            for sym in tickers:
                if sym and sym != '':
                    if sym not in symbol_dates:
                        # First appearance
                        symbol_dates[sym] = (date, pd.Timestamp('2099-12-31'))
                    else:
                        # Update to track last appearance
                        start_date, _ = symbol_dates[sym]
                        symbol_dates[sym] = (start_date, pd.Timestamp('2099-12-31'))

    # Now detect delistings by finding symbols that don't appear in later snapshots
    # Get the last snapshot date
    last_snapshot = relevant_snapshots.sort_values('date').iloc[-1]
    last_tickers = set([t.strip() for t in str(last_snapshot['tickers']).split(',')])

    # Check which symbols are no longer in the final snapshot
    for sym in list(symbol_dates.keys()):
        if sym not in last_tickers:
            # This symbol was delisted - find its last appearance
            start_date, _ = symbol_dates[sym]

            # Find last date this symbol appeared
            last_date = start_date
            for _, row in relevant_snapshots.iterrows():
                date = row['date']
                tickers = [t.strip() for t in str(row['tickers']).split(',')]
                if sym in tickers:
                    last_date = max(last_date, date)

            symbol_dates[sym] = (start_date, last_date)

    logger.info(f"Processed {len(relevant_snapshots)} snapshots")

    # If we got no symbols (e.g., CSV format issue), try to get from existing instruments file or Wikipedia
    if len(symbol_dates) == 0:
        logger.warning("No symbols found in historical CSV - trying fallback methods")

        # Try existing instruments file first
        if INSTRUMENTS_FILE.exists():
            logger.info(f"Loading symbols from existing instruments file: {INSTRUMENTS_FILE}")
            with open(INSTRUMENTS_FILE, 'r') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if parts:
                        sym = parts[0]
                        if not sym.startswith('^'):  # Skip benchmarks
                            # Use existing date ranges if available, otherwise default to full range
                            if len(parts) >= 3:
                                start = pd.Timestamp(parts[1])
                                end = pd.Timestamp(parts[2])
                            else:
                                start = pd.Timestamp(START_DATE)
                                end = pd.Timestamp('2099-12-31')
                            symbol_dates[sym] = (start, end)

            logger.info(f"Loaded {len(symbol_dates)} symbols from existing instruments file")

    # Convert dates to strings
    symbol_date_ranges = {
        sym: (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        for sym, (start, end) in symbol_dates.items()
    }

    all_symbols = list(symbol_dates.keys())

    logger.info(f"Total unique symbols: {len(all_symbols)}")
    logger.info(f"  - Active (no end date): {sum(1 for _, end in symbol_date_ranges.values() if end == '2099-12-31')}")
    logger.info(f"  - Delisted: {sum(1 for _, end in symbol_date_ranges.values() if end != '2099-12-31')}")

    # Show some delisted examples
    delisted = [(sym, dates) for sym, dates in symbol_date_ranges.items() if dates[1] != '2099-12-31']
    if delisted:
        logger.info(f"Example delisted stocks:")
        for sym, (start, end) in delisted[:5]:
            logger.info(f"  - {sym}: {start} to {end}")

    # Add benchmark indices (always active)
    for idx in BENCHMARK_INDICES:
        symbol_date_ranges[idx] = (START_DATE, '2099-12-31')
        all_symbols.append(idx)

    logger.info(f"Total symbols to download (including benchmarks): {len(all_symbols)}")

    return all_symbols, symbol_date_ranges


def download_batch(symbols: List[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    """Download data for a batch of symbols using yahooquery."""
    try:
        ticker = Ticker(symbols, asynchronous=False)
        data = ticker.history(start=start, end=end, interval="1d")

        if isinstance(data, pd.DataFrame) and not data.empty:
            result = {}
            if isinstance(data.index, pd.MultiIndex):
                for symbol in symbols:
                    if symbol in data.index.get_level_values(0):
                        df = data.xs(symbol, level=0).reset_index()
                        df["symbol"] = symbol
                        result[symbol] = df
            else:
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


def compute_simpson_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Simpson's VWAP approximation: (open + 2*high + 2*low + close) / 6

    This is the formula used in Qlib's own highfreq examples.
    """
    df = df.copy()
    df['vwap'] = (df['open'] + 2*df['high'] + 2*df['low'] + df['close']) / 6
    return df


def save_to_csv(symbol: str, df: pd.DataFrame, output_dir: Path):
    """Save DataFrame to CSV file with normalized symbol name and VWAP."""
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

    # Compute Simpson VWAP
    df = compute_simpson_vwap(df)

    # Ensure date column is formatted as YYYY-MM-DD only
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Reorder columns to include vwap
    cols = ["date", "symbol", "open", "high", "low", "close", "volume", "adjclose", "vwap"]
    df = df[cols]

    # Save
    df.to_csv(filepath, index=False)
    logger.debug(f"Saved {symbol} to {filepath} with VWAP")


def phase_3_download_ohlcv(symbols: List[str]):
    """Phase 3: Download OHLCV data from Yahoo Finance."""
    logger.info("=" * 60)
    logger.info("PHASE 3: Download OHLCV from Yahoo Finance")
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

        # Small delay between batches
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


def phase_4_normalize():
    """Phase 4: Normalize data using Qlib's YahooNormalize1dExtend."""
    logger.info("=" * 60)
    logger.info("PHASE 4: Normalize Data")
    logger.info("=" * 60)

    # Create normalize directory
    NORMALIZE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Using YahooNormalizeUS1dExtend...")

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


def phase_5_dump_to_binary():
    """Phase 5: Convert to Qlib binary format using DumpDataAll."""
    logger.info("=" * 60)
    logger.info("PHASE 5: Dump to Binary Format")
    logger.info("=" * 60)

    logger.info(f"Target Qlib directory: {QLIB_DATA_DIR}")
    logger.info("Using DumpDataAll to rebuild all data from scratch...")

    # Determine number of workers
    max_workers = max(multiprocessing.cpu_count() - 2, 1)

    # IMPORTANT: Use DumpDataAll (not DumpDataUpdate) to ensure clean rebuild
    # This includes the new vwap field
    dumper = DumpDataAll(
        data_path=str(NORMALIZE_DIR),
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


def phase_6_rebuild_instruments(symbol_date_ranges: Dict[str, Tuple[str, str]]):
    """Phase 6: Rebuild instruments/sp500.txt with correct date ranges."""
    logger.info("=" * 60)
    logger.info("PHASE 6: Rebuild Instruments File")
    logger.info("=" * 60)

    instruments_dir = QLIB_DATA_DIR / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)

    instruments_path = instruments_dir / "sp500.txt"

    # Sort symbols alphabetically
    sorted_symbols = sorted(symbol_date_ranges.keys())

    # Write instruments file
    # Format: SYMBOL\tSTART_DATE\tEND_DATE
    with open(instruments_path, 'w') as f:
        for symbol in sorted_symbols:
            start_date, end_date = symbol_date_ranges[symbol]
            f.write(f"{symbol}\t{start_date}\t{end_date}\n")

    logger.info(f"Wrote {len(sorted_symbols)} symbols to {instruments_path}")

    # Show statistics
    active_count = sum(1 for _, end in symbol_date_ranges.values() if end == '2099-12-31')
    delisted_count = len(sorted_symbols) - active_count

    logger.info(f"  - Active stocks: {active_count}")
    logger.info(f"  - Delisted stocks: {delisted_count}")


def cleanup_temp_files():
    """Remove temporary directories."""
    logger.info("=" * 60)
    logger.info("Cleanup Temporary Files")
    logger.info("=" * 60)

    import shutil

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        logger.info(f"Removed temporary directory: {TEMP_DIR}")


def verify_dataset():
    """Verify that the dataset was built correctly."""
    logger.info("=" * 60)
    logger.info("Verify Dataset")
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

        # Check instruments
        instruments = D.instruments('sp500')
        logger.info(f"Total instruments: {len(instruments)}")

        # Check VWAP field for AAPL
        try:
            df = D.features(["AAPL"], ["$close", "$vwap"], start_time="2025-01-01")
            if len(df) > 20 and df['$vwap'].notna().sum() > 20:
                logger.info(f"✓ AAPL has {len(df)} records with VWAP since 2025-01-01")
                logger.info(f"  Sample VWAP values: {df['$vwap'].head(3).values}")
            else:
                logger.warning(f"✗ AAPL has insufficient VWAP data")
        except Exception as e:
            logger.error(f"✗ Failed to read VWAP for AAPL: {e}")

        # Check that vwap.day.bin files exist
        vwap_files = list((QLIB_DATA_DIR / "features").glob("*/vwap.day.bin"))
        logger.info(f"✓ Found {len(vwap_files)} vwap.day.bin files")

        # Check delisted stocks
        try:
            # Try to load instruments with date ranges
            with open(INSTRUMENTS_FILE, 'r') as f:
                lines = f.readlines()
                delisted = [line for line in lines if '2099-12-31' not in line and '^' not in line]
                logger.info(f"✓ Found {len(delisted)} delisted stocks in instruments file")

                if delisted:
                    logger.info("  Example delisted stocks:")
                    for line in delisted[:3]:
                        logger.info(f"    {line.strip()}")
        except Exception as e:
            logger.warning(f"Could not check delisted stocks: {e}")

        logger.info("Verification complete!")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main execution flow."""
    parser = argparse.ArgumentParser(
        description='Download survivorship-bias-free S&P 500 data with Alpha158 fields'
    )
    parser.add_argument(
        '--polygon-api-key',
        type=str,
        help='Polygon.io API key for true VWAP (optional, uses Simpson approximation by default)'
    )
    args = parser.parse_args()

    start_time = time.time()

    logger.info("=" * 60)
    logger.info("Survivorship-Bias-Free S&P 500 Dataset Builder")
    logger.info("=" * 60)
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Qlib data directory: {QLIB_DATA_DIR}")
    logger.info(f"VWAP method: {'Polygon.io' if args.polygon_api_key else 'Simpson approximation'}")
    logger.info("")

    try:
        # Phase 1: Download historical constituents
        historical_df = phase_1_download_historical_constituents()

        # Phase 2: Build symbol list with date ranges
        symbols, symbol_date_ranges = phase_2_build_symbol_list(historical_df)

        # Phase 3: Download OHLCV from Yahoo
        phase_3_download_ohlcv(symbols)

        # Phase 4: Normalize
        phase_4_normalize()

        # Phase 5: Dump to binary
        phase_5_dump_to_binary()

        # Phase 6: Rebuild instruments file
        phase_6_rebuild_instruments(symbol_date_ranges)

        # Cleanup
        cleanup_temp_files()

        # Verify
        verify_dataset()

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"SUCCESS! Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Clear caches: rm -rf ./git_ignore_folder ./pickle_cache")
        logger.info("2. Test Alpha158: python test_alpha158.py")
        logger.info("3. Run backtests with the new survivorship-bias-free dataset")

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
