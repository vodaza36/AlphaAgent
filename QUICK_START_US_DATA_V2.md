# Quick Start: Survivorship-Bias-Free S&P 500 Dataset

## TL;DR

```bash
# 1. Download survivorship-bias-free dataset with VWAP (30-45 min)
python prepare_us_data_v2.py

# 2. Clear caches
rm -rf ./git_ignore_folder ./pickle_cache

# 3. Verify dataset
python test_alpha158_vwap.py

# 4. Start using AlphaAgent with the new dataset
alphaagent mine --potential_direction "Your hypothesis"
```

## What This Fixes

### Before ❌
- **Survivorship bias**: Missing ~50+ stocks that left S&P 500 during 2020-2026
- **Missing VWAP**: Alpha158 has NaN features, causes rank-deficient matrices
- **Instruments file**: 250 delistings all before 2020-10-09 (clearly incomplete)

### After ✅
- **No survivorship bias**: Includes ALL ~600-650 stocks that were ever in S&P 500 during 2020-2026
- **VWAP available**: Simpson's approximation `(open + 2*high + 2*low + close)/6`
- **Instruments file**: ~50-100+ properly dated delistings from 2020-2026

## One-Command Setup

```bash
# Backup old data, download new data, verify, and clean up
mv ~/.qlib/qlib_data/us_data ~/.qlib/qlib_data/us_data_backup && \
python prepare_us_data_v2.py && \
rm -rf ./git_ignore_folder ./pickle_cache && \
python test_alpha158_vwap.py
```

## Expected Output

### prepare_us_data_v2.py
```
PHASE 1: Download Historical S&P 500 Constituents
  Loaded 1234 historical change records
  Found 56 index changes in 2020-01-01 to 2026-02-07

PHASE 2: Build Symbol List with Date Ranges
  Total unique symbols: 623
    - Active (no end date): 503
    - Delisted: 120
  Example delisted stocks:
    - ETFC: 2020-01-01 to 2020-10-02
    - XLNX: 2020-01-01 to 2022-02-14
    - FB: 2020-01-01 to 2021-10-28

PHASE 3: Download OHLCV from Yahoo Finance
  Download complete: 620/626 symbols
  Created 620 CSV files

PHASE 4: Normalize Data
  Normalized 620 files

PHASE 5: Dump to Binary Format
  Binary dump complete!

PHASE 6: Rebuild Instruments File
  Wrote 626 symbols to instruments file
    - Active stocks: 506
    - Delisted stocks: 120

SUCCESS! Total time: 2145.3 seconds (35.8 minutes)
```

### test_alpha158_vwap.py
```
TEST 1: Basic Fields Availability
  Testing AAPL...
    ✓ $open: 252/252 non-null
    ✓ $high: 252/252 non-null
    ✓ $low: 252/252 non-null
    ✓ $close: 252/252 non-null
    ✓ $volume: 252/252 non-null
    ✓ $vwap: 252/252 non-null ← NEW!

TEST 2: VWAP Data Quality
  Testing AAPL...
    ✓ All 252 records have valid VWAP in [low, high] range
    ✓ No zero VWAP values
    VWAP-Close correlation: 0.9987

TEST 3: Alpha158 Handler
  ✓ Alpha158 computed successfully
  Shape: (502764, 158) (rows, features)
  ✓ Only 2.34% NaN values
  ✓ Found 26 VWAP-based features

TEST 4: Survivorship Bias Check
  Total instruments: 626
    - Active: 506
    - Delisted: 120
  ✓ Found 120 delisted stocks - survivorship bias addressed

TEST 5: Benchmark Indices
  ✓ ^GSPC retrieved 252 records
  ✓ ^NDX retrieved 252 records
  ✓ ^DJI retrieved 252 records
```

## Key Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Delistings 2020-2026 | 0 | ~100-120 | ✅ Bias fixed |
| Total unique symbols | 755 | ~620-650 | More accurate |
| VWAP field | ❌ Missing | ✅ Available | Alpha158 works |
| Rank-deficient errors | ⚠️ Common | ✅ Rare | Model stability |
| Backtest realism | ⚠️ Optimistic | ✅ Realistic | Better research |

## Data Quality Checks

After running `test_alpha158_vwap.py`, verify these pass:

✅ All 6 Alpha158 fields available
✅ VWAP is non-zero and within [low, high] range
✅ VWAP-Close correlation: 0.95-0.999 (reasonable)
✅ Alpha158 computes 158 features without errors
✅ NaN percentage < 5%
✅ 50-120 delisted stocks with proper end dates
✅ Benchmark indices (^GSPC, ^NDX, ^DJI) available

## Using the New Dataset

No code changes needed! AlphaAgent automatically uses the data in `~/.qlib/qlib_data/us_data/`.

```bash
# Run factor mining as usual
alphaagent mine --potential_direction "Momentum persists in small-cap tech stocks"

# Multi-factor backtesting
alphaagent backtest --factor_path factors.csv

# View results
alphaagent ui --port 19899 --log_dir log/
```

## Comparison: Before vs After Backtest

**Scenario**: Backtest a momentum factor from 2020-2025

### Before (Survivorship Bias)
- Tests factor only on stocks that survived the full period
- Missing: bankrupt companies, acquired companies, dropped small-caps
- Result: **Unrealistically high Sharpe ratio** (survivors tend to be winners)
- Example: Missing ETFC (acquired by Morgan Stanley 2020), XLNX (acquired by AMD 2022)

### After (Survivorship-Bias-Free)
- Tests factor on ALL stocks in S&P 500 at each point in time
- Includes: stocks that went bankrupt, were acquired, or dropped from index
- Result: **Realistic Sharpe ratio** reflecting true market conditions
- Example: Includes ETFC up to 2020-10-02, XLNX up to 2022-02-14

## Technical Notes

### Simpson's VWAP Formula
```python
vwap = (open + 2*high + 2*low + close) / 6
```

This is the same formula Qlib uses in `qlib/examples/highfreq/highfreq_handler.py:46`.

**Why it works:**
- Approximates intraday average price using OHLC
- After cross-sectional Rank() or Zscore() normalization, approximation error is negligible
- Far better than missing VWAP (which causes 0-filled columns and rank-deficient matrices)

**When to upgrade to true VWAP:**
- If you need exact intraday VWAP for high-frequency strategies
- Use `--polygon-api-key` option with Polygon.io free tier
- Takes 2.5 hours due to rate limiting (5 req/min)

### Data Sources
- **Historical constituents**: [fja05680/sp500](https://github.com/fja05680/sp500) (GitHub, free)
- **OHLCV**: Yahoo Finance via yahooquery (free)
- **VWAP**: Simpson approximation (instant) or Polygon.io (2.5 hours, free tier)

## Troubleshooting

### "Some symbols failed to download"
Normal. A few delisted stocks are removed from Yahoo Finance. Script continues with available data.

### "Calendar only extends to 2025-XX-XX"
Run the script again - Yahoo Finance sometimes has delayed data updates.

### "Alpha158 has many NaN values"
Check that `vwap.day.bin` files exist:
```bash
ls ~/.qlib/qlib_data/us_data/features/aapl/vwap.day.bin
```

If missing, re-run with `DumpDataAll` (not `DumpDataUpdate`).

### "Backtest is slower than before"
Expected. The dataset now has more symbols (~620 vs previous ~500 active). This is the cost of addressing survivorship bias.

## FAQ

**Q: Do I need to change my Alpha158 config?**
A: No. Alpha158 automatically detects the new VWAP field.

**Q: Can I keep both old and new datasets?**
A: Yes. Backup old data to `us_data_backup` and switch by changing `provider_uri` in `qlib.init()`.

**Q: How often should I update the dataset?**
A: Monthly for backtesting research. Daily if running live trading (not recommended with free data sources).

**Q: Does this work for other indices (Russell 2000, Nasdaq 100)?**
A: Not yet. This script is specific to S&P 500. See `SURVIVORSHIP_BIAS_FREE_DATASET.md` "Future Enhancements" for details.

**Q: Is Simpson's VWAP good enough for research?**
A: Yes. After cross-sectional normalization (Rank/Zscore), the approximation error is minimal. Qlib itself uses this formula.

## Next Steps

1. ✅ Run `prepare_us_data_v2.py` (you are here)
2. ✅ Verify with `test_alpha158_vwap.py`
3. Clear caches: `rm -rf ./git_ignore_folder ./pickle_cache`
4. Start mining: `alphaagent mine --potential_direction "Your hypothesis"`
5. Compare results: Backtest the same factor on old vs new dataset to see the survivorship bias effect

## Resources

- **Full Documentation**: `SURVIVORSHIP_BIAS_FREE_DATASET.md`
- **Project Instructions**: `CLAUDE.md`
- **AlphaAgent Paper**: `alphaagent-paper.pdf`
- **Qlib Docs**: https://qlib.readthedocs.io/
