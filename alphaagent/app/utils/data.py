"""
Data management utilities for AlphaAgent.

Provides functions to initialize, verify, and refresh Qlib market data.
"""

from __future__ import annotations

import sys
import time
import shutil
import zipfile
import multiprocessing
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import requests
from loguru import logger
from tqdm import tqdm
from yahooquery import Ticker

from alphaagent.core.conf import RD_AGENT_SETTINGS


def get_data_dir() -> Path:
    """
    Get the resolved Qlib data directory path.

    Returns:
        Path to the Qlib data directory (e.g., .data/us_data/)
    """
    data_uri = RD_AGENT_SETTINGS.qlib_data_uri
    return Path(data_uri).expanduser().resolve()


def get_data_zip_path() -> Path:
    """
    Get the path to the bundled data ZIP file.

    Returns:
        Path to data/us_data.zip in the project root
    """
    # Assume project root is 3 levels up from this file
    # alphaagent/app/utils/data.py -> ../../.. -> project root
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "data" / "us_data.zip"


def is_data_initialized() -> bool:
    """
    Check if Qlib data has been extracted and initialized.

    Returns:
        True if data is ready, False otherwise
    """
    data_dir = get_data_dir()

    # Check for key directories and files
    calendars_dir = data_dir / "calendars"
    instruments_dir = data_dir / "instruments"
    features_dir = data_dir / "features"

    if not all([calendars_dir.exists(), instruments_dir.exists(), features_dir.exists()]):
        return False

    # Check that instruments file exists
    sp500_instruments = instruments_dir / "sp500.txt"
    if not sp500_instruments.exists():
        return False

    # Check that we have some feature data
    if not list(features_dir.glob("*/*.bin")):
        return False

    return True


def init(force: bool = False) -> None:
    """
    Extract bundled Qlib data ZIP to the data directory.

    Args:
        force: If True, overwrite existing data. If False, skip if already initialized.

    Raises:
        FileNotFoundError: If the data ZIP file doesn't exist
        RuntimeError: If extraction fails
    """
    data_dir = get_data_dir()
    zip_path = get_data_zip_path()

    # Check if data is already initialized
    if is_data_initialized() and not force:
        logger.info(f"Data already initialized at {data_dir}")
        logger.info("Use `alphaagent init --force` to re-extract")
        return

    # Verify ZIP file exists
    if not zip_path.exists():
        raise FileNotFoundError(
            f"Data ZIP not found at {zip_path}\n"
            f"Please run `alphaagent data-refresh` to download and build the dataset."
        )

    logger.info("=" * 60)
    logger.info("Initializing Qlib Data")
    logger.info("=" * 60)
    logger.info(f"Source ZIP: {zip_path}")
    logger.info(f"Target directory: {data_dir}")

    # Remove existing data if force mode
    if force and data_dir.exists():
        logger.info("Removing existing data...")
        shutil.rmtree(data_dir)

    # Create data directory
    data_dir.mkdir(parents=True, exist_ok=True)

    # Extract ZIP
    try:
        logger.info("Extracting data ZIP...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)

        logger.info(f"Extracted {len(list(data_dir.rglob('*')))} files")

        # Verify extraction
        if not is_data_initialized():
            raise RuntimeError("Data extraction completed but verification failed")

        logger.info("=" * 60)
        logger.info("Data initialization complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("You can now run:")
        logger.info("  alphaagent mine --potential_direction \"<YOUR_HYPOTHESIS>\"")

    except Exception as e:
        logger.error(f"Failed to extract data: {e}")
        raise RuntimeError(f"Data initialization failed: {e}")


def data_refresh() -> None:
    """
    Download latest S&P 500 data, rebuild Qlib binary format, and update the ZIP.

    This function:
    1. Downloads historical S&P 500 constituents from GitHub
    2. Builds symbol list with date ranges (including delisted stocks)
    3. Downloads OHLCV data from Yahoo Finance
    4. Computes Simpson's VWAP approximation
    5. Normalizes data using Qlib's YahooNormalizeUS1dExtend
    6. Dumps to Qlib binary format
    7. Rebuilds instruments file with delisting dates
    8. Re-creates data/us_data.zip

    This is adapted from prepare_us_data_v2.py
    """
    # Add qlib scripts to path
    project_root = Path(__file__).parent.parent.parent.parent
    qlib_scripts = project_root / "qlib" / "scripts"
    sys.path.insert(0, str(qlib_scripts))
    sys.path.insert(0, str(qlib_scripts / "data_collector" / "yahoo"))

    from dump_bin import DumpDataAll
    from data_collector.yahoo.collector import YahooNormalizeUS1dExtend
    from data_collector.base import Normalize
    from qlib.utils import code_to_fname

    # Configuration
    data_dir = get_data_dir()
    temp_dir = project_root / "temp_us_data_refresh"
    source_dir = temp_dir / "source"
    normalize_dir = temp_dir / "normalize"
    historical_csv_path = temp_dir / "sp500_historical.csv"

    # Date range
    START_DATE = "2020-01-01"
    END_DATE = pd.Timestamp.now().strftime("%Y-%m-%d")

    # Historical constituents URL
    HISTORICAL_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes(01-17-2026).csv"

    # Benchmark indices
    BENCHMARK_INDICES = ["^GSPC", "^NDX", "^DJI"]

    # Batch size for Yahoo queries
    BATCH_SIZE = 20

    logger.info("=" * 60)
    logger.info("Data Refresh: Downloading Latest S&P 500 Data")
    logger.info("=" * 60)
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Target directory: {data_dir}")
    logger.info("")

    try:
        # Phase 1: Download historical constituents
        logger.info("Phase 1: Downloading historical constituents...")
        temp_dir.mkdir(parents=True, exist_ok=True)

        response = requests.get(HISTORICAL_URL, timeout=30)
        response.raise_for_status()

        with open(historical_csv_path, 'wb') as f:
            f.write(response.content)

        historical_df = pd.read_csv(historical_csv_path)
        logger.info(f"Downloaded {len(historical_df)} historical change records")

        # Phase 2: Build symbol list with date ranges
        logger.info("Phase 2: Building symbol list with date ranges...")
        symbols, symbol_date_ranges = _build_symbol_list(historical_df, START_DATE, END_DATE, BENCHMARK_INDICES)

        # Phase 3: Download OHLCV from Yahoo
        logger.info("Phase 3: Downloading OHLCV data from Yahoo Finance...")
        source_dir.mkdir(parents=True, exist_ok=True)
        _download_ohlcv(symbols, START_DATE, END_DATE, source_dir, BATCH_SIZE)

        # Phase 4: Normalize data
        logger.info("Phase 4: Normalizing data...")
        normalize_dir.mkdir(parents=True, exist_ok=True)

        normalizer = Normalize(
            source_dir=str(source_dir),
            target_dir=str(normalize_dir),
            normalize_class=YahooNormalizeUS1dExtend,
            max_workers=8,
            date_field_name="date",
            symbol_field_name="symbol",
            old_qlib_data_dir=str(data_dir),
        )
        normalizer.normalize()

        # Phase 5: Dump to binary format
        logger.info("Phase 5: Converting to Qlib binary format...")
        max_workers = max(multiprocessing.cpu_count() - 2, 1)

        dumper = DumpDataAll(
            data_path=str(normalize_dir),
            qlib_dir=str(data_dir),
            include_fields="open,high,low,close,volume,adjclose,vwap",
            exclude_fields="symbol,date",
            max_workers=max_workers,
            freq="day",
            date_field_name="date",
            symbol_field_name="symbol",
        )
        dumper.dump()

        # Phase 6: Rebuild instruments file
        logger.info("Phase 6: Rebuilding instruments file...")
        _rebuild_instruments(data_dir, symbol_date_ranges)

        # Phase 7: Rebuild ZIP file
        logger.info("Phase 7: Rebuilding data ZIP...")
        _rebuild_zip(data_dir)

        # Cleanup
        logger.info("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)

        logger.info("=" * 60)
        logger.info("Data refresh complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Data refresh failed: {e}")
        raise RuntimeError(f"Data refresh failed: {e}")


def _build_symbol_list(
    historical_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    benchmark_indices: List[str]
) -> Tuple[List[str], Dict[str, Tuple[str, str]]]:
    """Build symbol list with date ranges from historical constituents data."""
    historical_df['date'] = pd.to_datetime(historical_df['date'])

    # Filter to date range
    mask = (historical_df['date'] >= start_date) & (historical_df['date'] <= end_date)
    relevant_snapshots = historical_df[mask].copy()

    logger.info(f"Found {len(relevant_snapshots)} daily snapshots")

    # Track symbol dates
    symbol_dates: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]] = {}

    for _, row in relevant_snapshots.iterrows():
        date = row['date']

        if 'tickers' in row and pd.notna(row['tickers']):
            tickers = [t.strip() for t in str(row['tickers']).split(',')]

            for sym in tickers:
                if sym and sym != '':
                    if sym not in symbol_dates:
                        symbol_dates[sym] = (date, pd.Timestamp('2099-12-31'))
                    else:
                        start_date_inner, _ = symbol_dates[sym]
                        symbol_dates[sym] = (start_date_inner, pd.Timestamp('2099-12-31'))

    # Detect delistings
    last_snapshot = relevant_snapshots.sort_values('date').iloc[-1]
    last_tickers = set([t.strip() for t in str(last_snapshot['tickers']).split(',')])

    for sym in list(symbol_dates.keys()):
        if sym not in last_tickers:
            start_date_inner, _ = symbol_dates[sym]
            last_date = start_date_inner

            for _, row in relevant_snapshots.iterrows():
                date = row['date']
                tickers = [t.strip() for t in str(row['tickers']).split(',')]
                if sym in tickers:
                    last_date = max(last_date, date)

            symbol_dates[sym] = (start_date_inner, last_date)

    # Convert to string dates
    symbol_date_ranges = {
        sym: (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        for sym, (start, end) in symbol_dates.items()
    }

    all_symbols = list(symbol_dates.keys())

    logger.info(f"Total unique symbols: {len(all_symbols)}")
    logger.info(f"  Active: {sum(1 for _, end in symbol_date_ranges.values() if end == '2099-12-31')}")
    logger.info(f"  Delisted: {sum(1 for _, end in symbol_date_ranges.values() if end != '2099-12-31')}")

    # Add benchmark indices
    for idx in benchmark_indices:
        symbol_date_ranges[idx] = (start_date, '2099-12-31')
        all_symbols.append(idx)

    return all_symbols, symbol_date_ranges


def _download_ohlcv(symbols: List[str], start_date: str, end_date: str, output_dir: Path, batch_size: int) -> None:
    """Download OHLCV data from Yahoo Finance."""
    from qlib.utils import code_to_fname

    downloaded = 0
    failed = []

    for i in tqdm(range(0, len(symbols), batch_size), desc="Downloading batches"):
        batch = symbols[i:i + batch_size]

        try:
            ticker = Ticker(batch, asynchronous=False)
            data = ticker.history(start=start_date, end=end_date, interval="1d")

            if isinstance(data, pd.DataFrame) and not data.empty:
                if isinstance(data.index, pd.MultiIndex):
                    for symbol in batch:
                        if symbol in data.index.get_level_values(0):
                            df = data.xs(symbol, level=0).reset_index()
                            df["symbol"] = symbol
                            _save_to_csv(symbol, df, output_dir)
                            downloaded += 1
                else:
                    data = data.reset_index()
                    data["symbol"] = batch[0]
                    _save_to_csv(batch[0], data, output_dir)
                    downloaded += 1
        except Exception as e:
            logger.warning(f"Batch download failed: {e}")
            failed.extend(batch)

        time.sleep(0.5)

    logger.info(f"Downloaded {downloaded}/{len(symbols)} symbols")


def _save_to_csv(symbol: str, df: pd.DataFrame, output_dir: Path) -> None:
    """Save DataFrame to CSV with VWAP computation."""
    from qlib.utils import code_to_fname

    if df.empty:
        return

    filename = code_to_fname(symbol).upper() + ".csv"
    filepath = output_dir / filename

    required_cols = ["date", "open", "high", "low", "close", "volume", "symbol"]
    for col in required_cols:
        if col not in df.columns:
            return

    if "adjclose" not in df.columns:
        df["adjclose"] = df["close"]

    # Compute Simpson's VWAP: (open + 2*high + 2*low + close) / 6
    df = df.copy()
    df['vwap'] = (df['open'] + 2*df['high'] + 2*df['low'] + df['close']) / 6

    # Format date
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Reorder columns
    cols = ["date", "symbol", "open", "high", "low", "close", "volume", "adjclose", "vwap"]
    df = df[cols]

    df.to_csv(filepath, index=False)


def _rebuild_instruments(data_dir: Path, symbol_date_ranges: Dict[str, Tuple[str, str]]) -> None:
    """Rebuild instruments/sp500.txt file with date ranges."""
    instruments_dir = data_dir / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)

    instruments_path = instruments_dir / "sp500.txt"

    sorted_symbols = sorted(symbol_date_ranges.keys())

    with open(instruments_path, 'w') as f:
        for symbol in sorted_symbols:
            start_date, end_date = symbol_date_ranges[symbol]
            f.write(f"{symbol}\t{start_date}\t{end_date}\n")

    logger.info(f"Wrote {len(sorted_symbols)} symbols to instruments file")


def _rebuild_zip(data_dir: Path) -> None:
    """Rebuild data/us_data.zip from the data directory."""
    zip_path = get_data_zip_path()
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove old ZIP if exists
    if zip_path.exists():
        zip_path.unlink()

    logger.info(f"Creating {zip_path}...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in data_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(data_dir)
                zipf.write(file_path, arcname)

    logger.info(f"Created ZIP: {zip_path} ({zip_path.stat().st_size / (1024*1024):.1f} MB)")
