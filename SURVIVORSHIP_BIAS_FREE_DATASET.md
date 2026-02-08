# Survivorship-Bias-Free S&P 500 Dataset with Alpha158 Fields

## Overview

This implementation addresses two critical issues in the original US stock dataset:

1. **Survivorship Bias**: The original dataset had ~250 historical delistings, but ALL occurred before 2020-10-09. This means ~50+ index changes during 2020-2026 were missing, creating survivorship bias in backtests.

2. **Missing VWAP**: Alpha158 requires 6 fields (`$open`, `$high`, `$low`, `$close`, `$volume`, `$vwap`), but Yahoo Finance only provides 5 (no VWAP). The missing VWAP field caused rank-deficient matrices in some models.

## Solution

### Survivorship Bias
- Uses historical S&P 500 constituent data from **fja05680/sp500** GitHub repository
- Covers 1996-2026 with complete addition/removal history
- Includes ALL stocks that were ever in the S&P 500 during 2020-2026, not just current constituents
- Properly sets end dates for delisted stocks (not 2099-12-31)

### VWAP Field
- Uses **Simpson's approximation**: `VWAP = (open + 2*high + 2*low + close) / 6`
- This is the same formula used in Qlib's own `qlib/examples/highfreq/highfreq_handler.py:46`
- After cross-sectional normalization, the approximation error is minimal
- Alternative: Can optionally use Polygon.io free tier for true VWAP (2.5 hours download time)

## Data Sources

| Component | Source | Quality | Cost |
|-----------|--------|---------|------|
| Historical S&P 500 constituents | [fja05680/sp500](https://github.com/fja05680/sp500) (GitHub) | High | Free |
| OHLCV price data | Yahoo Finance (yahooquery) | High | Free |
| VWAP data | Simpson's formula from OHLC | Good | Free |
| VWAP data (optional) | Polygon.io free tier | Excellent | Free (5 req/min limit) |
| Benchmark indices | Yahoo Finance | High | Free |

## Files

- **prepare_us_data_v2.py**: Main script to download and prepare the survivorship-bias-free dataset
- **test_alpha158_vwap.py**: Verification script to test Alpha158 compatibility and data quality

## Usage

### Step 1: Backup Existing Data (Optional)

```bash
# Backup current dataset
mv ~/.qlib/qlib_data/us_data ~/.qlib/qlib_data/us_data_backup
```

### Step 2: Run the Data Preparation Script

```bash
# Download and prepare survivorship-bias-free dataset with Simpson VWAP
python prepare_us_data_v2.py

# OR with true VWAP from Polygon.io (requires free API key)
python prepare_us_data_v2.py --polygon-api-key YOUR_API_KEY
```

**Estimated time:**
- With Simpson VWAP: 30-45 minutes
- With Polygon VWAP: 3-4 hours (due to rate limiting)

### Step 3: Clear Caches

```bash
# Remove cached backtest results and experiment workspaces
rm -rf ./git_ignore_folder ./pickle_cache

# Remove old daily_pv files (if they exist)
rm -f ~/.qlib/qlib_data/us_data/factor_data_template/daily_pv_all.h5
rm -f ~/.qlib/qlib_data/us_data/factor_data_template/daily_pv_debug.h5
```

### Step 4: Verify the Dataset

```bash
# Run verification tests
python test_alpha158_vwap.py
```

Expected output:
- ✓ All 6 Alpha158 fields available
- ✓ VWAP data is valid (not zeros, within [low, high] range)
- ✓ Alpha158 handler computes features without errors
- ✓ 50-100+ delisted stocks included in instruments file
- ✓ Benchmark indices (^GSPC, ^NDX, ^DJI) available

### Step 5: Update Backtest Configurations

The dataset is now ready to use with AlphaAgent. No configuration changes needed - the system will automatically use the new data.

## Dataset Statistics

### Before (Original Dataset)
- Total symbols: 755
- Delisted stocks with end dates < 2026: ~250 (all before 2020-10-09)
- Missing delistings 2020-2026: ~50+
- VWAP field: Missing (causes rank-deficient matrices)
- Survivorship bias: **YES**

### After (New Dataset)
- Total symbols: ~600-650 unique symbols
- Active stocks: ~503 (current S&P 500)
- Delisted stocks 2020-2026: ~50-100+ (properly tracked)
- VWAP field: **Available** (Simpson approximation or Polygon.io)
- Survivorship bias: **NO** (addresses bias for 2020-2026 period)

## Technical Details

### Historical Constituent Data Format

The fja05680/sp500 CSV has columns: `date, added, removed`

Example:
```csv
date,added,removed
2023-05-01,"DECK",""
2023-05-01,"","ZION"
2024-03-18,"DECK,KKR","DRE,IVZ"
```

The script parses this to build a symbol registry with proper start/end dates.

### Instruments File Format

The rebuilt `~/.qlib/qlib_data/us_data/instruments/sp500.txt` has format:
```
SYMBOL\tSTART_DATE\tEND_DATE
```

Example:
```
AAPL	2020-01-01	2099-12-31
ETFC	2020-01-01	2020-10-02
FB	2020-01-01	2021-10-28
META	2021-10-29	2099-12-31
```

### VWAP Computation

Simpson's VWAP is computed as:
```python
vwap = (open + 2*high + 2*low + close) / 6
```

This approximation:
- Is used in Qlib's own high-frequency examples
- Provides reasonable estimates of intraday average price
- After cross-sectional normalization (Rank, Zscore), the error is minimal
- Is far better than missing VWAP (which causes 0-filled columns)

### Binary Data Structure

The script uses `DumpDataAll` (not `DumpDataUpdate`) to rebuild the entire dataset from scratch, ensuring:
- Clean calendar without gaps
- Proper instrument date ranges
- All 6 required fields including `vwap.day.bin`

Directory structure:
```
~/.qlib/qlib_data/us_data/
├── calendars/
│   └── day.txt
├── instruments/
│   └── sp500.txt
└── features/
    ├── aapl/
    │   ├── open.day.bin
    │   ├── high.day.bin
    │   ├── low.day.bin
    │   ├── close.day.bin
    │   ├── volume.day.bin
    │   ├── adjclose.day.bin
    │   └── vwap.day.bin  ← NEW!
    ├── msft/
    │   └── ...
    └── ...
```

## Verification Checklist

After running the data preparation script, verify:

- [ ] Calendar extends to 2026-02-06+
- [ ] Instruments file has ~600-650 symbols
- [ ] Active stocks: ~503 with end date 2099-12-31
- [ ] Delisted stocks: ~50-100+ with end dates in 2020-2026
- [ ] VWAP field exists: `ls ~/.qlib/qlib_data/us_data/features/aapl/vwap.day.bin`
- [ ] VWAP is accessible: `D.features(["AAPL"], ["$vwap"], start_time="2025-01-01")`
- [ ] Alpha158 computes without errors
- [ ] No rank-deficient matrix warnings in model training

## Known Limitations

1. **Delisted Stock Data Availability**: Yahoo Finance sometimes removes data for bankrupted/acquired companies after delisting. The script downloads data as early as possible, but a small number (<5) of obscure delistings might have incomplete data. Use Polygon.io fallback if needed.

2. **VWAP Approximation**: Simpson's VWAP is an approximation, not true tick-level VWAP. For research requiring true VWAP, use the `--polygon-api-key` option.

3. **Ticker Symbol Changes**: The script handles common ticker changes (FB→META, GOOG→GOOGL), but some edge cases might require manual mapping.

4. **Index Changes Before 2020**: The script focuses on 2020-2026. If you need earlier data, the fja05680/sp500 repository covers back to 1996.

## Troubleshooting

### "Failed to download symbol X"
Some delisted stocks might be unavailable on Yahoo Finance. This is expected for a small number of bankruptcies. The script will continue with available symbols.

### "VWAP is highly correlated with close (>0.99)"
This indicates VWAP approximation is very close to closing price for that stock. This is normal for low-volatility stocks. After rank normalization, this won't affect factor performance.

### "Verification failed: vwap.day.bin not found"
Ensure you used `DumpDataAll` (not `DumpDataUpdate`) and included `vwap` in the `include_fields` parameter.

### "Alpha158 returns NaN for VWAP features"
Check that:
1. VWAP binary files exist: `ls ~/.qlib/qlib_data/us_data/features/*/vwap.day.bin | wc -l`
2. Qlib can read VWAP: `python -c "import qlib; from qlib.data import D; qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us'); print(D.features(['AAPL'], ['\$vwap'], start_time='2025-01-01'))"`

## References

- **Historical S&P 500 Data**: [fja05680/sp500](https://github.com/fja05680/sp500)
- **Cross-Validation Source**: [riazarbi/sp500-scraper](https://github.com/riazarbi/sp500-scraper)
- **Qlib Documentation**: [Microsoft Qlib](https://github.com/microsoft/qlib)
- **Simpson's VWAP in Qlib**: `qlib/examples/highfreq/highfreq_handler.py:46`
- **Qlib Yahoo Data Limitations**: [Issue #274](https://github.com/microsoft/qlib/issues/274)

## Citation

If you use this survivorship-bias-free dataset in research, please cite:

1. **AlphaAgent** (KDD 2025): The original framework this project is based on
2. **fja05680/sp500**: The historical constituent data source
3. **Microsoft Qlib**: The quantitative investment framework

## Future Enhancements

Potential improvements for future versions:

1. **Automated Daily Updates**: GitHub Actions workflow to update the dataset daily
2. **Polygon.io Integration**: Fully integrated true VWAP download with progress tracking
3. **Russell 2000/3000 Support**: Extend to other indices beyond S&P 500
4. **Corporate Actions**: Handle stock splits, dividends, and mergers more explicitly
5. **Fundamental Data**: Add quarterly earnings, revenue, and other fundamental features

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review `test_alpha158_vwap.py` output for specific error messages
3. Open an issue in the AlphaAgent repository
