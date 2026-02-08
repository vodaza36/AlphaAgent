# Survivorship-Bias-Free S&P 500 Dataset - Setup Checklist

Use this checklist to ensure your dataset is correctly prepared and verified.

## Pre-Installation

- [ ] Python 3.10 environment activated
- [ ] Qlib installed: `pip list | grep qlib`
- [ ] Required packages installed: `yahooquery`, `pandas`, `numpy`, `loguru`, `tqdm`, `requests`
- [ ] Backup existing data (optional): `mv ~/.qlib/qlib_data/us_data ~/.qlib/qlib_data/us_data_backup`

## Installation

- [ ] Run data preparation: `python prepare_us_data_v2.py`
- [ ] Script completed successfully (no errors in final summary)
- [ ] Total time was 30-45 minutes (or 3-4 hours if using Polygon.io)
- [ ] Success message displayed

## Verification - Basic Checks

- [ ] Calendar extends to 2026:
  ```bash
  python -c "import qlib; from qlib.data import D; qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us'); print(f'Calendar: {D.calendar()[0]} to {D.calendar()[-1]}')"
  ```

- [ ] Instruments file exists: `ls ~/.qlib/qlib_data/us_data/instruments/sp500.txt`

- [ ] Instruments file has 600-650 entries:
  ```bash
  wc -l ~/.qlib/qlib_data/us_data/instruments/sp500.txt
  ```

- [ ] VWAP binary files exist (check for AAPL as example):
  ```bash
  ls ~/.qlib/qlib_data/us_data/features/aapl/vwap.day.bin
  ```

- [ ] Count total VWAP files (should be ~600-650):
  ```bash
  ls ~/.qlib/qlib_data/us_data/features/*/vwap.day.bin | wc -l
  ```

## Verification - Run Test Script

- [ ] Run verification script: `python test_alpha158_vwap.py`

- [ ] **TEST 1: Basic Fields Availability** - All PASS
  - [ ] AAPL has all 6 fields
  - [ ] MSFT has all 6 fields
  - [ ] GOOGL has all 6 fields
  - [ ] VWAP is non-null and non-zero

- [ ] **TEST 2: VWAP Data Quality** - All PASS
  - [ ] VWAP is within [low, high] range
  - [ ] No zero VWAP values
  - [ ] VWAP-Close correlation: 0.95-0.999

- [ ] **TEST 3: Alpha158 Handler** - PASS
  - [ ] Alpha158 computed successfully
  - [ ] Shape: (>400000, 158)
  - [ ] NaN percentage < 5%
  - [ ] Found VWAP-based features

- [ ] **TEST 4: Survivorship Bias Check** - PASS
  - [ ] Total instruments: 600-650
  - [ ] Active stocks: ~500-510
  - [ ] Delisted stocks: 50-150
  - [ ] Example delisted stocks shown

- [ ] **TEST 5: Benchmark Indices** - All PASS
  - [ ] ^GSPC available
  - [ ] ^NDX available
  - [ ] ^DJI available

## Post-Installation

- [ ] Clear caches:
  ```bash
  rm -rf ./git_ignore_folder ./pickle_cache
  ```

- [ ] Remove old daily_pv files (if they exist):
  ```bash
  rm -f ~/.qlib/qlib_data/us_data/factor_data_template/daily_pv_*.h5
  ```

- [ ] Test Qlib access:
  ```bash
  python -c "import qlib; from qlib.data import D; qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us'); print(D.features(['AAPL'], ['\$close', '\$vwap'], start_time='2025-01-01'))"
  ```

## Integration with AlphaAgent

- [ ] Test AlphaAgent can initialize with new data:
  ```bash
  python -c "from alphaagent.app.qlib_rd_loop.conf import AlphaAgentFactorBasePropSetting; print('✓ AlphaAgent imports work')"
  ```

- [ ] Run a quick factor mining test (optional):
  ```bash
  alphaagent mine --potential_direction "Test hypothesis: momentum persists" --max_iterations 1
  ```

## Troubleshooting

If any checks fail:

### "Calendar only extends to 2025-XX-XX"
- [ ] Re-run `prepare_us_data_v2.py` - Yahoo Finance may have delayed updates
- [ ] Check END_DATE in script is set to current date

### "VWAP files missing"
- [ ] Verify script used `DumpDataAll` (not `DumpDataUpdate`)
- [ ] Check `include_fields` parameter includes `vwap`
- [ ] Re-run dump_to_binary phase manually if needed

### "Too few delisted stocks (<20)"
- [ ] Check historical CSV was downloaded correctly
- [ ] Verify date parsing in phase_2_build_symbol_list
- [ ] Check Wikipedia current constituents fetch worked

### "Some symbols failed to download"
- [ ] Normal for a few delisted stocks
- [ ] If >50 failures, check Yahoo Finance API status
- [ ] Try increasing RETRY_DELAY and MAX_RETRIES

### "Alpha158 has many NaN values (>10%)"
- [ ] Check VWAP field is actually used in Alpha158 config
- [ ] Verify calendar has no gaps
- [ ] Ensure normalization completed successfully

## Final Validation

- [ ] Run a simple backtest to ensure no errors:
  ```bash
  # Create a simple factor CSV
  echo "factor_name,factor_expression" > test_factor.csv
  echo "SimpleMA,Mean(\$close, 20)" >> test_factor.csv

  # Run backtest
  alphaagent backtest --factor_path test_factor.csv
  ```

- [ ] Check backtest completes without errors
- [ ] Verify backtest report is generated
- [ ] Compare results to old dataset (if backup exists)

## Documentation Review

- [ ] Read `QUICK_START_US_DATA_V2.md` for quick reference
- [ ] Read `SURVIVORSHIP_BIAS_FREE_DATASET.md` for technical details
- [ ] Understand Simpson's VWAP formula
- [ ] Know how to check for survivorship bias in results

## Success Criteria

All of the following should be true:

- [x] Script completed in <60 minutes
- [x] 600-650 total symbols in dataset
- [x] 50-150 delisted stocks with proper end dates
- [x] All 6 Alpha158 fields available
- [x] Alpha158 computes 158 features
- [x] No rank-deficient matrix errors
- [x] AlphaAgent runs without errors
- [x] All verification tests pass

## Next Steps

Once all checks pass:

1. **Test existing factors**: Re-run your existing factors to see the impact of survivorship bias correction
2. **Compare results**: Benchmark new vs old dataset (expect ~10-30% performance difference)
3. **Mine new factors**: Use AlphaAgent with the new survivorship-bias-free data
4. **Update documentation**: Note which dataset version you used in research papers
5. **Schedule updates**: Plan monthly data refreshes

## Support

If you encounter issues not covered by this checklist:

1. Review the troubleshooting section in `SURVIVORSHIP_BIAS_FREE_DATASET.md`
2. Check script output logs for specific error messages
3. Verify all dependencies are correctly installed
4. Ensure sufficient disk space (~5GB for US data)
5. Check network connectivity (required for downloading from GitHub and Yahoo Finance)

## Maintenance

Regular maintenance tasks:

- [ ] **Monthly**: Re-run `prepare_us_data_v2.py` to get latest data
- [ ] **Quarterly**: Verify historical constituent data is up to date
- [ ] **Annually**: Review and update any ticker symbol mappings
- [ ] **Before major backtests**: Ensure data is current and caches are cleared

---

**Date Completed**: _____________

**Dataset Version**: US S&P 500 Survivorship-Bias-Free (2020-2026)

**VWAP Method**: [ ] Simpson Approximation  [ ] Polygon.io True VWAP

**Notes**:
