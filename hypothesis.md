# AlphaAgent Research Hypotheses

> Generated via `research-hypothesis` skill with 10 parallel agents on 2026-02-09.
> All factors use validated DSL functions and variables only (`$open`, `$close`, `$high`, `$low`, `$volume`, `$return`).
> State persisted in `.claude/research/hypotheses.json`.

---

## Hypothesis 1: Residual Momentum with Volume Confirmation

**ID:** `h_20260209_001` | **Theme:** `momentum-trend`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Construct volatility-normalized residual momentum factors that isolate firm-specific trend from market beta, confirmed by volume trend alignment, to capture decay-resistant alpha from idiosyncratic price continuation."
```

**Full hypothesis:**
Residual momentum -- the component of past returns orthogonal to market beta -- decays significantly slower than raw price momentum and avoids the long-term reversal that plagues conventional momentum strategies. Quantpedia and Blitz et al. show that ranking stocks on 12-month residual returns (standardized by residual volatility) produces risk-adjusted profits roughly twice those of total-return momentum, with only half the volatility and a monthly Sharpe ratio of 0.48 vs 0.25. We hypothesize that constructing a volatility-normalized, volume-confirmed residual trend signal will generate decay-resistant alpha in the S&P 500 universe.

**Suggested factors:**
1. `RANK(REGRESI($close, SEQUENCE(252), 252) / TS_STD(REGRESI($close, SEQUENCE(252), 252), 60))`
2. `DECAYLINEAR($close / TS_MEAN($close, 60) - 1, 20) * SIGN(TS_MEAN($volume, 10) - TS_MEAN($volume, 60))`
3. `RANK(TS_MEAN($return, 240) - TS_MEAN($return, 20)) / TS_STD($return, 60) * (COUNT($volume > TS_MEAN($volume, 60), 20) / 20)`

**Sources:**
- Residual Momentum Factor (Quantpedia)
- Momentum factor investing: Evidence and evolution (Baltussen et al., SSRN)

---

## Hypothesis 2: Volume-Conditioned Short-Term Reversal

**ID:** `h_20260209_002` | **Theme:** `mean-reversion`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Exploit short-term mean reversion by ranking stocks on volatility-normalized, volume-weighted 5-day return deviations from their rolling mean, going long oversold and short overbought names where abnormal volume signals liquidity-driven overreaction."
```

**Full hypothesis:**
Short-term return reversals are stronger when conditioned on abnormal volume and elevated volatility, consistent with microstructure-driven overreaction. Dai and Medhat (2024, Financial Analysts Journal) show that higher volatility produces faster and initially stronger reversals, while lower turnover leads to more persistent reversals. Da et al. demonstrate that the non-fundamental component of returns reverses more reliably, generating risk-adjusted alpha four times larger than unconditional reversal.

**Suggested factors:**
1. `RANK(TS_ZSCORE($close, 20) * -1)`
2. `RANK(($close - TS_MEAN($close, 5)) / TS_STD($close, 20) * ($volume / TS_MEAN($volume, 20)) * -1)`
3. `RANK(DECAYLINEAR($return * -1, 5) / TS_STD($return, 20))`

**Sources:**
- Reversals and the Returns to Liquidity Provision (Dai & Medhat, FAJ 2024)
- A Closer Look at the Short-Term Return Reversal (Da, Liu, Schaumburg)

---

## Hypothesis 3: Asymmetric Downside Volatility Premium

**ID:** `h_20260209_003` | **Theme:** `volatility-risk`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Go long stocks where downside semi-variance dominates total variance and where recent realized volatility has contracted relative to its longer-term average, exploiting the asymmetric IVOL pricing anomaly."
```

**Full hypothesis:**
Stocks with a higher ratio of downside realized semi-variance to total realized variance are underpriced and earn higher future returns, consistent with the asymmetric volatility pricing documented by Bollerslev, Li & Todorov (JFQA 2020) and Liu & Zhu (JBF 2025). The mechanism is that lottery-seeking investors overpay for upside-volatile stocks while underpricing stocks whose volatility comes predominantly from the downside, creating a cross-sectional return spread.

**Suggested factors:**
1. `RANK(SUMIF(POW($return, 2), 20, $return < 0) / (TS_SUM(POW($return, 2), 20) + 1e-8))`
2. `RANK((TS_STD($return, 60) - TS_STD($return, 20)) / (TS_STD($return, 60) + 1e-8))`
3. `RANK(SUMIF(POW($return, 2), 20, $return < 0) - SUMIF(POW($return, 2), 20, $return > 0))`

**Sources:**
- Good idiosyncratic volatility, bad idiosyncratic volatility (Liu & Zhu, JBF 2025)
- Good Volatility, Bad Volatility, and the Cross Section of Stock Returns (Bollerslev et al., JFQA 2020)

---

## Hypothesis 4: Abnormal Volume as Attention Signal

**ID:** `h_20260209_004` | **Theme:** `volume-liquidity`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Stocks with abnormally high volume relative to their 20-day average exhibit short-term return continuation driven by attention and sentiment, while volume-price divergence (rising price on falling volume) signals momentum exhaustion and predicts reversals."
```

**Full hypothesis:**
Abnormal trading volume is a strong short-term cross-sectional predictor of stock returns. Goyenko et al. (NBER 2024) demonstrate that the economic benefits of predicting individual stock volume are as large as those from return predictability itself. A 2024 European Journal of Finance study shows that extreme abnormal volume deciles generate positive returns in the short run followed by reversals. Volume-price divergence signals weakening momentum and impending reversals.

**Suggested factors:**
1. `RANK(TS_ZSCORE($volume, 20))`
2. `RANK(TS_CORR($volume, $close, 10))`
3. `RANK(DECAYLINEAR($volume / TS_MEAN($volume, 20) * SIGN(DELTA($close, 1)), 10))`

**Sources:**
- Trading Volume Alpha (Goyenko, Kelly, Moskowitz et al., NBER 2024)
- Persistence or reversal? Abnormal trading volume on stock returns (European Journal of Finance, 2024)

---

## Hypothesis 5: Cross-Sectional Dispersion Reversal

**ID:** `h_20260209_005` | **Theme:** `cross-sectional-dispersion`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Exploit cross-sectional return dispersion by going long stocks that are cross-sectionally cheap with high recent idiosyncratic volatility and poor short-term returns, as these high-dispersion-contribution stocks exhibit stronger mean-reversion tendencies."
```

**Full hypothesis:**
Cross-sectional return dispersion signals mean-reversion opportunities, particularly for mechanical factors. Hua & Sun (2024) show mechanical signals exhibit hyperbolic alpha decay under crowding, while judgment-based relative-value signals remain resilient. Seidl et al. (2025) demonstrate that conditioning on drift regimes amplifies cross-sectional predictability dramatically. Stocks contributing disproportionately to dispersion with poor recent performance exhibit stronger mean-reversion.

**Suggested factors:**
1. `INV(ZSCORE(TS_MEAN($return, 5)))`
2. `RANK(TS_STD($return, 20)) * RANK(INV(TS_SUM($return, 10)))`
3. `DECAYLINEAR(ZSCORE($return), 10) * INV(ZSCORE(TS_STD($return, 60)))`

**Sources:**
- Not All Factors Crowd Equally: Modeling, Measuring, and Trading on Alpha Decay (arXiv 2512.11913)
- Discovery of a 13-Sharpe OOS Factor: Drift Regimes (arXiv 2511.12490)

---

## Hypothesis 6: MACD-RSI Interaction Alpha

**ID:** `h_20260209_006` | **Theme:** `technical-patterns`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Construct cross-indicator interaction factors that multiply momentum signals (MACD direction, RSI rate-of-change) with volatility breakout signals (Bollinger Band position) and volume confirmation, then cross-sectionally rank them to capture regime-adaptive reversal and continuation patterns."
```

**Full hypothesis:**
Multiplicative interactions between momentum indicators (MACD) and mean-reversion oscillators (RSI, Bollinger Bands) capture nonlinear behavioral signals that standalone technical indicators miss. Li et al. (2025) found the MACD-RSI product was the single highest-attributed alpha factor in SHAP analysis. A hybrid trading system (Ravi et al., 2026) achieved a Sharpe ratio of 1.68 by combining trend-following via MACD with mean-reversion via RSI and Bollinger Bands.

**Suggested factors:**
1. `RANK(MACD($close) * (RSI($close, 14) - 50))`
2. `RANK(($close - BB_UPPER($close, 20)) * ($volume / TS_MEAN($volume, 20)))`
3. `RANK(DELTA(RSI($close, 14), 5) * SIGN(MACD($close)))`

**Sources:**
- Deep Learning for Short-Term Equity Trend Forecasting (Li et al., arXiv 2508.14656)
- Generating Alpha: A Hybrid AI-Driven Trading System (Ravi et al., arXiv 2601.19504)

---

## Hypothesis 7: Drift Regime-Gated Reversal

**ID:** `h_20260209_007` | **Theme:** `regime-change`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Construct regime-aware alpha factors that gate short-term reversal signals by stock-level drift regime indicators (fraction of positive return days over 63 days) and use volatility regime ratios (short-term vs long-term realized volatility) to switch between mean-reversion and momentum strategies."
```

**Full hypothesis:**
Stocks exhibit distinct "drift regimes" detectable via the fraction of positive return days, and alpha signals are dramatically more effective when conditioned on regime state. Li et al. (2025) demonstrate that gating reversal signals by a drift regime indicator (>60% positive days in 63-day window) boosts Sharpe ratios from 1.2 to 13.2 out-of-sample. Complementary work shows that short-term vs. long-term volatility ratios reliably detect bull-bear regime transitions, reducing maximum drawdowns by ~50%.

**Suggested factors:**
1. `FILTER(-TS_ZSCORE($return, 10), COUNT($return > 0, 63) > 38)`
2. `RANK(TS_STD($return, 10) / TS_STD($return, 60))`
3. `(TS_STD($return, 10) / TS_STD($return, 60) > 1) ? (-TS_ZSCORE($return, 5)) : (TS_MEAN($return, 20))`

**Sources:**
- Discovery of a 13-Sharpe OOS Factor: Drift Regimes (arXiv 2511.12490)
- Dynamic Factor Allocation Leveraging Regime-Switching Signals (arXiv 2410.14841)

---

## Hypothesis 8: Order Flow Imbalance via Close Location

**ID:** `h_20260209_008` | **Theme:** `order-flow-microstructure`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Go long stocks with strong positive volume-weighted close-location accumulation (indicating persistent buy-side flow dominance) and short stocks with negative accumulation, exploiting the autocorrelation of order flow imbalance and asymmetric price impact."
```

**Full hypothesis:**
Stocks exhibiting persistent directional order flow imbalance, proxied by the close location within the daily range weighted by volume, generate predictable short-term return continuation. Chordia et al. demonstrate that daily order imbalances are positively autocorrelated and that sell imbalances have roughly four times the price impact of buy imbalances. Federal Reserve research (2025) confirms that sustained unidirectional flow magnitude amplifies price movements.

**Suggested factors:**
1. `RANK(TS_SUM(($close - $low - ($high - $close)) / ($high - $low + 0.0001) * $volume, 10))`
2. `SUMIF($volume, 10, $return > 0) / (SUMIF($volume, 10, $return < 0) + 0.0001)`
3. `TS_CORR($volume * SIGN($return), DELAY($volume * SIGN($return), 1), 20)`

**Sources:**
- Order Imbalance, Liquidity, and Market Returns (Chordia, Roll, Subrahmanyam)
- Order Flow Imbalances and Amplification of Price Movements (Federal Reserve, 2025)

---

## Hypothesis 9: Overnight Return Premium Exploitation

**ID:** `h_20260209_009` | **Theme:** `overnight-intraday`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Go long stocks with persistently high overnight returns relative to intraday returns, and short stocks where intraday returns consistently dominate, exploiting the retail-driven overnight premium and the systematic overnight-intraday reversal pattern."
```

**Full hypothesis:**
Nearly all U.S. equity premium accrues overnight rather than during trading hours, with cumulative overnight returns exceeding intraday returns by ~7.2% annually (arXiv 2507.04481). This overnight-intraday split exhibits a persistent negative contemporaneous correlation: stocks performing well intraday tend to underperform overnight and vice versa. Perreten and Wallmeier (2024) show that intraday volume patterns predict overnight returns, with U-shaped volume stocks earning higher overnight premiums.

**Suggested factors:**
1. `TS_MEAN(($open - DELAY($close, 1)) / DELAY($close, 1), 5)`
2. `RANK(TS_MEAN(($open - DELAY($close, 1)) / DELAY($close, 1), 10)) - RANK(TS_MEAN(($close - $open) / $open, 10))`
3. `(($open - DELAY($close, 1)) / DELAY($close, 1)) / TS_STD($return, 20)`

**Sources:**
- Does Overnight News Explain Overnight Returns? (arXiv 2507.04481, 2025)
- Overnight Returns and the Timing of Trading Volume (Perreten & Wallmeier, SSRN 2024)

---

## Hypothesis 10: Realized Skewness Tail Risk Premium

**ID:** `h_20260209_010` | **Theme:** `skewness-tail-risk`

**Direction** (copy-paste ready):
```bash
alphaagent mine --potential_direction "Go long stocks with more negative realized skewness and higher downside tail frequency over the past month, as these carry a tail risk premium reflecting investor aversion to left-tail crash events and lottery-ticket preference for positively-skewed payoffs."
```

**Full hypothesis:**
Stocks exhibiting more negative realized return skewness and greater frequency of extreme downside moves earn higher subsequent returns, driven by a tail risk premium. Amaya et al. (JFE 2015) demonstrate that sorting stocks by realized skewness generates a significant negative return spread (19 bps/week, t=3.70). Kelly and Jiang (NBER 2014) show individual stock tail risk exposure is positively priced in the cross-section. A 2024 JBF study finds that decomposing volatility into good vs. bad components reveals downside asymmetry significantly predicts future returns.

**Suggested factors:**
1. `RANK(TS_MEAN(POW($return, 3), 20) / POW(TS_STD($return, 20), 3))`
2. `RANK(COUNT($return < TS_MEAN($return, 60) - 2 * TS_STD($return, 60), 20))`
3. `RANK(SUMIF(POW($return, 2), 20, $return < 0) / (SUMIF(POW($return, 2), 20, $return > 0) + 1e-8))`

**Sources:**
- Does Realized Skewness Predict the Cross-Section of Equity Returns? (Amaya et al., JFE 2015)
- Tail Risk and Asset Prices (Kelly & Jiang, NBER 2014)

---

## Summary Table

| # | ID | Theme | Hypothesis Title | Key Signal |
|---|-----|-------|-----------------|------------|
| 1 | h_20260209_001 | momentum-trend | Residual Momentum with Volume Confirmation | Volatility-normalized regression residual + volume trend |
| 2 | h_20260209_002 | mean-reversion | Volume-Conditioned Short-Term Reversal | Z-score reversal weighted by abnormal volume |
| 3 | h_20260209_003 | volatility-risk | Asymmetric Downside Volatility Premium | Downside semi-variance / total variance ratio |
| 4 | h_20260209_004 | volume-liquidity | Abnormal Volume as Attention Signal | Volume z-score + volume-price divergence |
| 5 | h_20260209_005 | cross-sectional-dispersion | Cross-Sectional Dispersion Reversal | Inverse z-score of recent returns * volatility rank |
| 6 | h_20260209_006 | technical-patterns | MACD-RSI Interaction Alpha | MACD * RSI product + BB breakout with volume |
| 7 | h_20260209_007 | regime-change | Drift Regime-Gated Reversal | COUNT positive days gating + vol regime ternary |
| 8 | h_20260209_008 | order-flow-microstructure | Order Flow Imbalance via Close Location | Close-location-value accumulated * volume |
| 9 | h_20260209_009 | overnight-intraday | Overnight Return Premium Exploitation | Overnight vs intraday return persistence |
| 10 | h_20260209_010 | skewness-tail-risk | Realized Skewness Tail Risk Premium | Realized skewness + downside tail count |
