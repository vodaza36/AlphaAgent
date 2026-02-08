#!/usr/bin/env python3
"""
Test Alpha158 handler with the new survivorship-bias-free US dataset.

This script verifies that:
1. All 6 required fields are available ($open, $high, $low, $close, $volume, $vwap)
2. VWAP field contains valid data (not zeros or NaNs)
3. Alpha158 features can be computed without errors
4. Historical delisted stocks are properly included

Usage:
    python test_alpha158_vwap.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

# Use installed qlib, not local repository
import qlib
from qlib.data import D
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP


def test_basic_fields():
    """Test that all 6 Alpha158 fields are available."""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Fields Availability")
    logger.info("=" * 60)

    fields = ["$open", "$high", "$low", "$close", "$volume", "$vwap"]
    test_symbols = ["AAPL", "MSFT", "GOOGL"]

    for symbol in test_symbols:
        logger.info(f"Testing {symbol}...")

        try:
            df = D.features([symbol], fields, start_time="2024-01-01", end_time="2026-01-01")

            if df.empty:
                logger.error(f"  ✗ No data returned for {symbol}")
                continue

            logger.info(f"  ✓ Retrieved {len(df)} records")

            # Check each field
            for field in fields:
                if field not in df.columns:
                    logger.error(f"    ✗ Missing field: {field}")
                else:
                    non_null = df[field].notna().sum()
                    non_zero = (df[field] != 0).sum()
                    logger.info(f"    ✓ {field}: {non_null}/{len(df)} non-null, {non_zero}/{len(df)} non-zero")

                    # Show sample values
                    sample = df[field].dropna().head(3).values
                    logger.info(f"      Sample values: {sample}")

        except Exception as e:
            logger.error(f"  ✗ Failed to retrieve data for {symbol}: {e}")

    logger.info("")


def test_vwap_quality():
    """Test VWAP data quality."""
    logger.info("=" * 60)
    logger.info("TEST 2: VWAP Data Quality")
    logger.info("=" * 60)

    test_symbols = ["AAPL", "MSFT", "GOOGL", "JPM", "XOM"]

    for symbol in test_symbols:
        logger.info(f"Testing {symbol}...")

        try:
            df = D.features(
                [symbol],
                ["$open", "$high", "$low", "$close", "$vwap"],
                start_time="2025-01-01",
                end_time="2026-01-01"
            )

            if df.empty:
                logger.warning(f"  ⚠ No data for {symbol}")
                continue

            # Check VWAP is between low and high
            valid_vwap = (df["$vwap"] >= df["$low"]) & (df["$vwap"] <= df["$high"])
            invalid_count = (~valid_vwap).sum()

            if invalid_count > 0:
                logger.warning(f"  ⚠ {invalid_count}/{len(df)} records have VWAP outside [low, high] range")
            else:
                logger.info(f"  ✓ All {len(df)} records have valid VWAP in [low, high] range")

            # Check VWAP is not all zeros
            zero_count = (df["$vwap"] == 0).sum()
            if zero_count > 0:
                logger.error(f"  ✗ {zero_count}/{len(df)} records have VWAP = 0")
            else:
                logger.info(f"  ✓ No zero VWAP values")

            # Check correlation with close (should be high but not 1.0)
            corr = df["$vwap"].corr(df["$close"])
            logger.info(f"  VWAP-Close correlation: {corr:.4f}")

            if corr > 0.99:
                logger.warning(f"  ⚠ VWAP is highly correlated with close ({corr:.4f}) - might be using close as proxy")
            elif corr > 0.90:
                logger.info(f"  ✓ VWAP has reasonable correlation with close")
            else:
                logger.warning(f"  ⚠ VWAP correlation with close is low ({corr:.4f})")

        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")

    logger.info("")


def test_alpha158_handler():
    """Test Alpha158 handler can compute features without errors."""
    logger.info("=" * 60)
    logger.info("TEST 3: Alpha158 Handler")
    logger.info("=" * 60)

    try:
        # Create Alpha158 handler
        from qlib.contrib.data.handler import Alpha158

        logger.info("Initializing Alpha158 handler...")

        handler = Alpha158(
            instruments="sp500",
            start_time="2021-01-01",
            end_time="2025-12-31",
            freq="day",
            infer_processors=[],
            learn_processors=[],
            fit_start_time="2021-01-01",
            fit_end_time="2022-12-31",
        )

        logger.info("Fetching Alpha158 features...")
        df = handler.fetch(col_set="feature")

        if df.empty:
            logger.error("  ✗ Alpha158 returned empty DataFrame")
            return

        logger.info(f"  ✓ Alpha158 computed successfully")
        logger.info(f"  Shape: {df.shape} (rows, features)")
        logger.info(f"  Date range: {df.index.get_level_values('datetime').min()} to {df.index.get_level_values('datetime').max()}")
        logger.info(f"  Unique instruments: {df.index.get_level_values('instrument').nunique()}")

        # Check for NaN values
        nan_count = df.isna().sum().sum()
        nan_pct = 100 * nan_count / (df.shape[0] * df.shape[1])

        if nan_pct > 10:
            logger.warning(f"  ⚠ {nan_pct:.2f}% of values are NaN (might indicate missing data)")
        else:
            logger.info(f"  ✓ Only {nan_pct:.2f}% NaN values")

        # Show sample features that use VWAP
        vwap_features = [col for col in df.columns if 'VWAP' in str(col).upper()]
        if vwap_features:
            logger.info(f"  ✓ Found {len(vwap_features)} VWAP-based features:")
            for feat in vwap_features[:5]:
                logger.info(f"    - {feat}")

    except Exception as e:
        logger.error(f"  ✗ Alpha158 handler failed: {e}")
        import traceback
        traceback.print_exc()

    logger.info("")


def test_survivorship_bias():
    """Test that delisted stocks are included in the dataset."""
    logger.info("=" * 60)
    logger.info("TEST 4: Survivorship Bias Check")
    logger.info("=" * 60)

    # Read instruments file
    instruments_file = Path.home() / ".qlib" / "qlib_data" / "us_data" / "instruments" / "sp500.txt"

    if not instruments_file.exists():
        logger.error(f"  ✗ Instruments file not found: {instruments_file}")
        return

    # Parse instruments
    instruments = []
    with open(instruments_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                symbol, start_date, end_date = parts[0], parts[1], parts[2]
                instruments.append((symbol, start_date, end_date))

    # Count active vs delisted
    active = [inst for inst in instruments if inst[2] == '2099-12-31']
    delisted = [inst for inst in instruments if inst[2] != '2099-12-31' and not inst[0].startswith('^')]

    logger.info(f"Total instruments: {len(instruments)}")
    logger.info(f"  - Active (end date = 2099-12-31): {len(active)}")
    logger.info(f"  - Delisted (end date < 2099-12-31): {len(delisted)}")

    if len(delisted) == 0:
        logger.error("  ✗ No delisted stocks found - dataset still has survivorship bias!")
        return
    elif len(delisted) < 20:
        logger.warning(f"  ⚠ Only {len(delisted)} delisted stocks - might be missing some delistings")
    else:
        logger.info(f"  ✓ Found {len(delisted)} delisted stocks - survivorship bias addressed")

    # Show examples of delisted stocks
    logger.info(f"\nExample delisted stocks:")
    for symbol, start_date, end_date in delisted[:10]:
        logger.info(f"  - {symbol}: {start_date} to {end_date}")

    # Test that we can retrieve data for a delisted stock
    if delisted:
        test_symbol = delisted[0][0]
        test_end_date = delisted[0][2]

        logger.info(f"\nTesting data retrieval for delisted stock {test_symbol}...")

        try:
            df = D.features(
                [test_symbol],
                ["$close"],
                start_time="2020-01-01",
                end_time=test_end_date
            )

            if df.empty:
                logger.warning(f"  ⚠ No data retrieved for {test_symbol}")
            else:
                logger.info(f"  ✓ Retrieved {len(df)} records for {test_symbol}")
                logger.info(f"    Data range: {df.index.get_level_values('datetime').min()} to {df.index.get_level_values('datetime').max()}")

        except Exception as e:
            logger.error(f"  ✗ Failed to retrieve data for {test_symbol}: {e}")

    logger.info("")


def test_benchmark_indices():
    """Test that benchmark indices are available."""
    logger.info("=" * 60)
    logger.info("TEST 5: Benchmark Indices")
    logger.info("=" * 60)

    benchmarks = ["^GSPC", "^NDX", "^DJI"]

    for symbol in benchmarks:
        logger.info(f"Testing {symbol}...")

        try:
            df = D.features([symbol], ["$close"], start_time="2025-01-01")

            if df.empty:
                logger.error(f"  ✗ No data for {symbol}")
            else:
                logger.info(f"  ✓ Retrieved {len(df)} records")

        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")

    logger.info("")


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Alpha158 VWAP Dataset Verification")
    logger.info("=" * 60)
    logger.info("")

    # Initialize Qlib
    qlib_data_dir = Path.home() / ".qlib" / "qlib_data" / "us_data"
    logger.info(f"Initializing Qlib with data directory: {qlib_data_dir}")

    try:
        qlib.init(provider_uri=str(qlib_data_dir), region="us")
        logger.info("✓ Qlib initialized successfully")
        logger.info("")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Qlib: {e}")
        sys.exit(1)

    # Run tests
    test_basic_fields()
    test_vwap_quality()
    test_alpha158_handler()
    test_survivorship_bias()
    test_benchmark_indices()

    logger.info("=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
