# AlphaAgent Data Guide

This document describes the market data bundled with AlphaAgent and how to manage it.

## Overview

AlphaAgent includes a **survivorship-bias-free S&P 500 dataset** covering 2020-2026 with approximately 600 symbols:
- **~500 active stocks** currently in the S&P 500 index
- **~100 delisted stocks** that left the index during this period
- **3 benchmark indices** (^GSPC, ^NDX, ^DJI)

This dataset enables realistic backtesting by including stocks that were removed from the index, preventing the artificial performance boost that comes from only testing on "survivors."

## Quick Start

### 1. Initialize Data (First Time Setup)

```bash
alphaagent init
```

This extracts the bundled market data from `data/us_data.zip` to `.data/us_data/`. Takes ~2 minutes.

### 2. Start Mining Factors

```bash
alphaagent mine --potential_direction "Your market hypothesis here"
```

That's it! The data is ready to use.

---

## Data Fields

Each stock has the following daily data fields:

| Field | Description |
|-------|-------------|
| `open` | Opening price |
| `high` | Highest price of the day |
| `low` | Lowest price of the day |
| `close` | Closing price |
| `volume` | Trading volume |
| `adjclose` | Adjusted close (accounts for splits/dividends) |
| `vwap` | Volume-weighted average price (Simpson's approximation) |
| `return` | Daily return (computed as pct_change of close) |

### VWAP Field

The `vwap` field uses **Simpson's approximation**:

```
vwap = (open + 2*high + 2*low + close) / 6
```

This approximation is used because true VWAP (volume-weighted tick data) is not available from free data sources. The Simpson approximation is sufficient for Alpha158 features and factor backtesting.

---

## Survivorship Bias Explained

**Survivorship bias** occurs when backtests only include stocks that "survived" until the present, ignoring stocks that were delisted, went bankrupt, or were removed from the index.

**Example**: If you backtest a strategy from 2020-2025 using only stocks currently in the S&P 500, you'll miss:
- Companies that went bankrupt (e.g., SVB Financial during 2023 banking crisis)
- Companies acquired by others
- Companies removed for underperformance

This creates an unrealistic "rosy" picture of strategy performance.

**Our solution**: The instruments file (`instruments/sp500.txt`) tracks the exact date range each stock was in the index:

```
AAPL    2020-01-01    2099-12-31    # Still active
DISCA   2020-01-01    2022-04-08    # Delisted (merged into WBD)
DWDP    2020-01-01    2021-06-01    # Delisted (split into DD and DOW)
```

Qlib automatically includes/excludes stocks based on these dates during backtesting.

---

## Time Periods

The dataset spans **2020-01-01 to 2026-02-07** with the following recommended splits:

| Split | Start Date | End Date | Purpose |
|-------|------------|----------|---------|
| **Train** | 2015-01-02 | 2022-12-31 | Model training |
| **Valid** | 2023-01-01 | 2024-12-31 | Hyperparameter tuning |
| **Test** | 2025-01-01 | 2026-02-07 | Final evaluation |

These periods are pre-configured in AlphaAgent's YAML templates.

---

## Refreshing Data

To download the latest market data and rebuild the dataset:

```bash
alphaagent data-refresh
```

This will:
1. Download historical S&P 500 constituents from GitHub ([fja05680/sp500](https://github.com/fja05680/sp500))
2. Build symbol list with exact date ranges (including delistings)
3. Download OHLCV data from Yahoo Finance via `yahooquery`
4. Compute Simpson's VWAP approximation
5. Normalize data using Qlib's `YahooNormalizeUS1dExtend`
6. Dump to Qlib binary format at `.data/us_data/`
7. Rebuild `data/us_data.zip` with the updated data

**Note**: This process takes 30-45 minutes and requires internet access.

---

## Custom Data Path

By default, data is stored at `.data/us_data/` relative to the project root. To use a different location, set the `QLIB_DATA_URI` environment variable:

```bash
export QLIB_DATA_URI="/path/to/your/qlib/data"
```

Or add it to your `.env` file:

```
QLIB_DATA_URI=/path/to/your/qlib/data
```

---

## Data Structure

The Qlib binary format is organized as follows:

```
.data/us_data/
├── calendars/
│   └── day.txt              # Trading calendar (list of valid trading days)
├── instruments/
│   └── sp500.txt            # Symbol list with date ranges
└── features/
    ├── AAPL/
    │   ├── open.day.bin     # Binary file for open prices
    │   ├── high.day.bin
    │   ├── low.day.bin
    │   ├── close.day.bin
    │   ├── volume.day.bin
    │   ├── adjclose.day.bin
    │   └── vwap.day.bin
    ├── MSFT/
    │   └── ...
    └── ^GSPC/               # Benchmark index
        └── ...
```

**Binary format advantages**:
- Fast random access for backtesting
- Memory-mapped file support
- Efficient storage (~10x smaller than CSV)

---

## Troubleshooting

### "Qlib data not initialized!"

Run `alphaagent init` to extract the bundled data.

### "Data already initialized"

The data is already extracted. Use `alphaagent init --force` to re-extract (overwrites existing data).

### "Data ZIP not found"

The `data/us_data.zip` file is missing. Run `alphaagent data-refresh` to download and build it from scratch.

### "VWAP field missing" errors

Ensure you're using the latest data. Run:
```bash
alphaagent init --force
```

If the error persists, rebuild the data:
```bash
alphaagent data-refresh
```

---

## Data Sources

- **Historical S&P 500 constituents**: [fja05680/sp500](https://github.com/fja05680/sp500) (updated monthly)
- **OHLCV price data**: Yahoo Finance via [yahooquery](https://yahooquery.dpguthrie.com/)
- **VWAP**: Simpson's approximation (computed locally)

All data sources are free and publicly available.

---

## Data Size

- **Compressed ZIP**: ~150-200 MB (depends on compression and included symbols)
- **Extracted directory**: ~500-800 MB (binary format)
- **Per symbol**: ~1-2 MB (6 years of daily data, 8 fields)

The data is small enough to commit to git without LFS.

---

## Advanced: Building Data from Scratch

If you want to build the data ZIP manually (e.g., for development):

```bash
# 1. Ensure you have Qlib data at ~/.qlib/qlib_data/us_data/
# (Run alphaagent data-refresh if needed)

# 2. Run the ZIP builder script
python scripts/build_data_zip.py

# 3. Verify the ZIP was created
ls -lh data/us_data.zip
```

The script will:
- Load symbols from `instruments/sp500.txt`
- Package only SP500 stocks + benchmark indices
- Strip unused fields (change, dividends, factor, splits)
- Compress to ~150-200 MB

---

## Questions?

For issues or questions about data:
1. Check this document first
2. Run `alphaagent init --force` to re-extract data
3. Run `alphaagent data-refresh` to rebuild from scratch
4. Report issues at: https://github.com/anthropics/claude-code/issues
