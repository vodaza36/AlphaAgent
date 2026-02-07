# Getting Started with AlphaAgent

Welcome to AlphaAgent! This guide will walk you through setting up and running AlphaAgent, an autonomous framework for mining interpretable and decay-resistant alpha factors using LLM agents. By the end of this guide, you'll have AlphaAgent running on US S&P 500 market data, generating and backtesting quantitative trading factors automatically.

## What is AlphaAgent?

AlphaAgent is a research framework that uses multiple AI agents working together to discover profitable trading signals (called "alpha factors") that resist the common problem of performance degradation over time ("alpha decay"). Unlike traditional quantitative research where human analysts manually craft factors, AlphaAgent automates this process using three specialized LLM agents.

### The Three-Agent System

<div align="center">
  <img src="docs/_static/workflow.png" alt="AlphaAgent Workflow" style="width:60%;">
</div>

AlphaAgent orchestrates three specialized agents in an iterative loop:

1. **Idea Agent**: Proposes market hypotheses based on financial theories, market phenomena, or emerging trends. For example: "momentum effects exist in equity markets where stocks with strong recent performance tend to continue outperforming."

2. **Factor Agent**: Translates hypotheses into concrete factor expressions using a domain-specific language (DSL). It incorporates regularization mechanisms to ensure factors are novel (not duplicates of existing factors) and maintains appropriate complexity to avoid overfitting.

3. **Eval Agent**: Executes backtests using the Qlib quantitative investment framework, evaluates performance metrics (IC, ICIR, returns, etc.), and provides detailed feedback. If a factor shows promise, it's added to the knowledge base; otherwise, the feedback guides the next iteration.

The workflow follows five pipeline steps:
- **Propose**: Idea Agent generates a market hypothesis
- **Construct**: Factor Agent creates factor expressions aligned with the hypothesis
- **Calculate**: Factor expressions are parsed and validated, then factor values are computed
- **Backtest**: Runner executes portfolio simulation with the factors
- **Feedback**: Eval Agent analyzes results and decides whether to accept or reject the factor

### The Alpha Decay Problem

In quantitative finance, "alpha" refers to excess returns beyond market benchmarks. However, most discovered factors suffer from **alpha decay**: their predictive power diminishes over time due to:
- Market regime changes
- Overcrowding (too many traders using the same signal)
- Overfitting to historical data

AlphaAgent combats alpha decay through:
- **AST-based novelty checks**: Analyzes the abstract syntax tree of factor expressions to ensure new factors differ structurally from existing ones
- **Complexity regularization**: Penalizes overly complex factors that are likely to overfit
- **Hypothesis alignment**: Ensures factors are grounded in interpretable market hypotheses rather than pure data mining
- **Iterative refinement**: Uses feedback loops to evolve factors that balance performance with robustness

### What You Get

After running AlphaAgent, you'll have:
- **Factor expressions**: Formulas like `(Rank($volume) * Rank(Ref($close, 1) - $close))` that can be used in trading strategies
- **Backtest reports**: Detailed performance metrics including IC (Information Coefficient), ICIR, annual returns, max drawdown, and Sharpe ratio
- **PnL charts**: Visual plots showing cumulative returns vs. benchmark over train/validation/test periods
- **Streamlit dashboard**: Interactive web UI to explore hypotheses, factors, and backtest results from all iterations

## Prerequisites

Before you begin, ensure you have:

### Required Software
- **Python 3.10 or 3.11**: AlphaAgent is well-tested on these versions
- **uv**: Fast Python package installer ([install guide](https://github.com/astral-sh/uv))
- **git**: For cloning repositories
- **macOS or Linux**: The factor mining timeout mechanism uses `signal.SIGALRM`, which is Unix-only. Windows users may encounter issues.

### Hardware & Storage
- **~2GB disk space** for Python environment and dependencies
- **~1GB disk space** for US S&P 500 stock data (2015-2024)
- **At least 4GB RAM** recommended for running backtests

### LLM API Access

You need an OpenAI-compatible API with:
- **Reasoning model**: For Idea Agent and Factor Agent (e.g., `deepseek-reasoner`, `o3-mini`, `o1-mini`)
- **Chat model**: For debugging and feedback generation (e.g., `deepseek-chat`, `gpt-4-turbo`, `gpt-4o`)

**Model Recommendations**:

| Provider | Reasoning Model | Chat Model | Cost | Quality |
|----------|----------------|------------|------|---------|
| DeepSeek | `deepseek-reasoner` | `deepseek-chat` | Very Low (~$0.50/day) | Good |
| OpenAI | `o3-mini` | `gpt-4-turbo` | Medium (~$5/day) | Excellent |
| OpenAI | `o1-mini` | `gpt-4o` | Medium (~$4/day) | Excellent |

*Cost estimates assume ~10 iterations per day. DeepSeek offers the best value for experimentation.*

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-repo/AlphaAgent.git
cd AlphaAgent
```

### Step 2: Create Virtual Environment

```bash
# Create environment with Python 3.10
uv venv --python 3.10

# Activate the environment
source .venv/bin/activate
```

### Step 3: Install AlphaAgent

```bash
# Install in editable mode
uv pip install -e .
```

### Step 4: Install Qlib

AlphaAgent requires Qlib for backtesting. Install from source:

```bash
# Clone Qlib repository
git clone https://github.com/microsoft/qlib.git
cd qlib

# Install Qlib
uv pip install .

# Return to AlphaAgent directory
cd ..
```

### Step 5: Verify Installation

```bash
# Check that alphaagent command is available
alphaagent --help
```

You should see output listing available commands: `mine`, `backtest`, `ui`, `health_check`, `collect_info`.

## Data Preparation — US Market

AlphaAgent can work with both Chinese (CSI500/CSI300) and US (S&P 500) stock markets. This guide focuses on US data.

### Download US S&P 500 Data

Qlib provides a built-in data downloader for US markets:

```bash
cd qlib

# Download US stock data to default location
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us

cd ..
```

This downloads:
- **Daily price data**: Open, high, low, close, volume for S&P 500 constituents
- **Calendar data**: Trading day calendar
- **Instrument universe**: List of stocks in the S&P 500 over time

The download may take 5-15 minutes depending on your connection.

### Verify Data

Check that data was downloaded correctly:

```bash
ls ~/.qlib/qlib_data/us_data/
```

You should see directories:
- `calendars/` — Trading calendar files
- `instruments/` — Stock universe definitions
- `features/` — Price and volume data in Qlib binary format

### Data Freshness

The Qlib data downloader provides data up to approximately the last few weeks. For the most recent data:
- The provided dataset is sufficient for backtesting and development
- For production use, consider setting up automated data updates
- Data typically covers 2015-2024 for US markets

## Configuration

### 6.1 Create `.env` File

Copy the example environment file and fill in your settings:

```bash
cp .env.example .env
```

Edit `.env` with your preferred text editor. Here's a minimal configuration:

**For DeepSeek API**:
```bash
# Global configs
USE_LOCAL=True
MAX_RETRY=5
RETRY_WAIT_SECONDS=5
FACTOR_MINING_TIMEOUT=10800

# LLM API Settings
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=sk-your-deepseek-api-key-here
REASONING_MODEL=deepseek-reasoner
CHAT_MODEL=deepseek-chat
EMBEDDING_MODEL=text-embedding-3-small

# Optional: Customize model parameters
CHAT_MAX_TOKENS=4000
CHAT_TEMPERATURE=0.7
```

**For OpenAI API**:
```bash
# Global configs
USE_LOCAL=True
MAX_RETRY=5
RETRY_WAIT_SECONDS=5
FACTOR_MINING_TIMEOUT=10800

# LLM API Settings
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-openai-api-key-here
REASONING_MODEL=o3-mini
CHAT_MODEL=gpt-4-turbo
EMBEDDING_MODEL=text-embedding-3-small

# Optional: Customize model parameters
CHAT_MAX_TOKENS=4000
CHAT_TEMPERATURE=0.7
```

**Required Variables**:
- `OPENAI_BASE_URL`: API endpoint URL
- `OPENAI_API_KEY`: Your API key
- `REASONING_MODEL`: Model for hypothesis generation and factor construction
- `CHAT_MODEL`: Model for debugging and feedback

**Important Settings**:
- `USE_LOCAL=True`: Run backtests locally (faster, recommended)
- `FACTOR_MINING_TIMEOUT=10800`: Maximum runtime in seconds (3 hours default)
- `MAX_RETRY=5`: Number of retries for failed API calls

### 6.2 Switch to US Market

By default, AlphaAgent is configured for Chinese markets (CSI500). To use US S&P 500 data, make the following changes:

#### Change 1: Update `conf.yaml`

Edit `alphaagent/scenarios/qlib/experiment/factor_template/conf.yaml`:

**Lines 1-13** — Uncomment US settings, comment CN settings:
```yaml
qlib_init:
    provider_uri: "~/.qlib/qlib_data/us_data"
    region: us

market: &market SP500
benchmark: &benchmark SPX

# qlib_init:
#     provider_uri: "~/.qlib/qlib_data/cn_data"
#     region: cn
#
# market: &market csi500
# benchmark: &benchmark SH000905
```

**Lines 75-80** — Update exchange costs to US values:
```yaml
exchange_kwargs:
    limit_threshold: 0.095
    deal_price: close
    open_cost: 0.0
    close_cost: 0.0005
    min_cost: 0
```

#### Change 2: Update `factor_runner.py`

Edit `alphaagent/scenarios/qlib/developer/factor_runner.py` at **line 121**:

Change:
```python
config_name = f"conf.yaml" if len(exp.based_experiments) == 0 else "conf_cn_combined_kdd_ver.yaml"
```

To:
```python
config_name = f"conf.yaml" if len(exp.based_experiments) == 0 else "conf_us_combined_kdd_ver.yaml"
```

#### Change 3: Update `generate.py`

Edit `alphaagent/scenarios/qlib/experiment/factor_data_template/generate.py` at **line 3**:

Change:
```python
qlib.init(provider_uri="~/.qlib/qlib_data/cn_data")
# qlib.init(provider_uri="~/.qlib/qlib_data/us_data")
```

To:
```python
# qlib.init(provider_uri="~/.qlib/qlib_data/cn_data")
qlib.init(provider_uri="~/.qlib/qlib_data/us_data")
```

#### Change 4: Clear Caches

After switching markets, clear all cached data:

```bash
# Remove cache directories
rm -rf ./pickle_cache/*
rm -rf ./git_ignore_folder/*

# Remove data generation files
rm -f alphaagent/scenarios/qlib/experiment/factor_data_template/daily_pv_all.h5
rm -f alphaagent/scenarios/qlib/experiment/factor_data_template/daily_pv_debug.h5
```

### 6.3 Optional Configuration Variables

Additional environment variables you can customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_AZURE` | `False` | Use Azure OpenAI instead of standard API |
| `CHAT_USE_AZURE_TOKEN_PROVIDER` | `False` | Use Azure token provider for chat model |
| `EMBEDDING_USE_AZURE_TOKEN_PROVIDER` | `False` | Use Azure token provider for embeddings |
| `MAX_RETRY` | `5` | Maximum API call retry attempts |
| `RETRY_WAIT_SECONDS` | `5` | Seconds to wait between retries |
| `FACTOR_MINING_TIMEOUT` | `10800` | Maximum runtime (seconds) before force quit |
| `USE_LOCAL` | `True` | Use local environment vs Docker for backtest |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model for RAG-based knowledge base |
| `CHAT_MAX_TOKENS` | `4000` | Maximum tokens in chat model responses |
| `CHAT_TEMPERATURE` | `0.7` | Temperature for chat model (0.0-1.0) |

## Your First Run

### 7.1 Start Factor Mining

Run AlphaAgent with a market hypothesis to guide factor discovery:

```bash
alphaagent mine --potential_direction "momentum-based factors using price and volume data"
```

The `--potential_direction` argument provides an initial hypothesis to bootstrap the Idea Agent. Be specific about:
- The market phenomenon you're interested in (momentum, mean reversion, volatility, etc.)
- The data sources to use (price, volume, fundamentals)
- Any constraints (short-term vs long-term, sector-specific, etc.)

**Alternative command** (equivalent):
```bash
dotenv run -- python alphaagent/app/qlib_rd_loop/factor_mining.py --direction "momentum-based factors using price and volume data"
```

### 7.2 What Happens During Execution

When you run `alphaagent mine`, the following pipeline executes iteratively:

1. **Factor Propose** (Idea Agent):
   - Analyzes your initial direction and any previous feedback
   - Generates a detailed market hypothesis with theoretical grounding
   - Example: "Stocks with high trading volume relative to their 20-day average and positive price momentum tend to continue outperforming in the short term."
   - Output: Hypothesis pickle saved to `r/hypothesis generation/<pid>/`

2. **Factor Construct** (Factor Agent):
   - Translates the hypothesis into 5-10 concrete factor expressions
   - Checks novelty against existing factors in knowledge base
   - Applies complexity regularization to avoid overfitting
   - Example expressions: `Rank($volume / Mean($volume, 20)) * Rank($close / Ref($close, 1) - 1)`
   - Output: Factor experiment pickle saved to `r/experiment generation/<pid>/`

3. **Factor Calculate** (Coder):
   - Parses factor expressions and validates syntax
   - Computes factor values across all stocks and time periods
   - Handles errors and debugging if expressions are malformed
   - Output: Factor values as pickled DataFrames in workspace

4. **Factor Backtest** (Runner):
   - Loads factor values into Qlib's backtesting framework
   - Trains LightGBM model on factor values
   - Simulates portfolio using TopkDropout strategy (buy top 50 stocks, rebalance daily)
   - Computes performance metrics: IC, ICIR, returns, Sharpe, max drawdown
   - Output: Backtest results pickle saved to `ef/runner result/<pid>/` with charts in `ef/Quantitative Backtesting Chart/<pid>/`

5. **Feedback** (Eval Agent):
   - Analyzes backtest metrics against acceptance thresholds
   - Checks for overfitting (train vs test performance gap)
   - Generates detailed feedback explaining accept/reject decision
   - If accepted: adds factor to knowledge base
   - If rejected: provides guidance for next iteration
   - Output: Feedback pickle saved to `ef/feedback/<pid>/` with detailed metrics in `ef/<pid>/common_logs.log`

The loop repeats, with each iteration learning from previous feedback. Typical runs execute 5-20 iterations before timeout or manual stop (Ctrl+C).

### 7.3 Example Hypotheses to Try

Here are well-tested market hypotheses for different trading phenomena:

**Momentum Strategies**:
```bash
alphaagent mine --potential_direction "momentum and trend-following signals based on price and volume patterns in equity markets"
```
Focus: Stocks with strong recent performance tend to continue outperforming

**Mean Reversion Strategies**:
```bash
alphaagent mine --potential_direction "mean reversion factors using short-term price deviations and volatility"
```
Focus: Stocks that deviate significantly from average prices tend to revert

**Volume-Price Divergence**:
```bash
alphaagent mine --potential_direction "volume-price divergence as a predictive signal for short-term returns"
```
Focus: Unusual volume patterns signal upcoming price movements

**Volatility-Adjusted Returns**:
```bash
alphaagent mine --potential_direction "volatility-adjusted returns for risk-based stock selection strategies"
```
Focus: Risk-adjusted performance metrics identify quality stocks

**Cross-Sectional Patterns**:
```bash
alphaagent mine --potential_direction "cross-sectional ranking factors based on relative price and volume strength"
```
Focus: Relative performance vs peers predicts future returns

### 7.4 Resuming a Session

If your session is interrupted or you want to continue from a previous run:

```bash
# Find your session directory
ls log/

# Resume from session directory
alphaagent mine --path log/<timestamp>/
```

AlphaAgent will load the previous state including:
- All generated hypotheses and factors
- Knowledge base with accepted factors
- Backtest results and feedback history
- Trace of all agent interactions

Continue running with `--step_n` to limit additional iterations:
```bash
alphaagent mine --path log/20250207_123456/ --step_n 5
```

### 7.5 Understanding Iterations and Stopping Conditions

**The mining process runs indefinitely by default** - there is no fixed maximum number of iterations. The workflow continues generating and testing new factors until explicitly stopped.

#### Iteration Structure

Each iteration consists of 5 sequential steps:
1. **factor_propose** - Idea Agent generates market hypothesis (~2-5 minutes)
2. **factor_construct** - Factor Agent creates factor expressions (~3-8 minutes)
3. **factor_calculate** - Calculates factor values (~1-3 minutes)
4. **factor_backtest** - Runs backtesting (~5-15 minutes)
5. **feedback** - Eval Agent validates and provides feedback (~1-3 minutes)

A complete iteration typically takes **12-30 minutes** depending on:
- LLM API response times
- Number of factors generated per iteration
- Size of the stock universe
- Model complexity (LightGBM training time)

#### When Mining Stops

The process stops when any of these conditions are met:

**1. Timeout (Default: 10 hours)**
- Configured in `.env` as `FACTOR_MINING_TIMEOUT=36000` (seconds)
- Prevents runaway processes and controls API costs
- Adjust for longer/shorter runs: `FACTOR_MINING_TIMEOUT=21600` (6 hours)

**2. Manual Termination**
- Press `Ctrl+C` to interrupt gracefully
- Session state is saved after each step for resumption
- Safe to interrupt at any point

**3. Step Limit (Optional)**
- Use `--step_n N` parameter to run exactly N steps
- Example: `alphaagent mine --direction "..." --step_n 20` runs 20 steps then stops
- Useful for controlled experiments or testing

**4. Fatal Errors**
- Non-recoverable exceptions terminate the process
- Note: `FactorEmptyError` (no valid factors generated) is handled gracefully - the loop skips that iteration and continues

#### Controlling Execution

**Run for specific duration**:
```bash
# 3 hours maximum
FACTOR_MINING_TIMEOUT=10800 alphaagent mine --potential_direction "your hypothesis"
```

**Run for specific iterations**:
```bash
# Run exactly 10 iterations (50 steps: 5 steps × 10 iterations)
alphaagent mine --potential_direction "your hypothesis" --step_n 50
```

**Resume and extend**:
```bash
# Resume previous session and run 5 more iterations (25 steps)
alphaagent mine --path log/20250207_123456/ --step_n 25
```

#### Monitoring Progress

Track iteration progress in real-time:
```bash
# Watch the log file
tail -f log/<timestamp>/<pid>/common_logs.log

# Or use the UI
alphaagent ui --port 19899 --log_dir log/
```

#### Expected Results

Based on typical runs:
- **First 3-5 iterations**: Initial exploration, higher rejection rate
- **Iterations 5-10**: Refined hypotheses, increasing acceptance rate
- **Iterations 10+**: Diminishing returns, most novel factors already discovered

**Recommendation**: Start with `--step_n 25` (5 iterations) to evaluate whether your hypothesis direction is productive, then extend if promising.

## Understanding the Output

### 8.1 Log Directory Structure

After running AlphaAgent, your `log/` directory contains:

```
log/
└── <timestamp>/
    ├── <pid>/                        # Process timing logs
    │   └── common_logs.log           # Step durations (e.g., "factor_propose took 170s")
    ├── __session__/                   # Session state snapshots (for resuming)
    │   ├── 0/                         # Loop iteration 0
    │   │   ├── 0_factor_propose       # State after hypothesis proposal (pickle)
    │   │   ├── 1_factor_construct     # State after factor construction (pickle)
    │   │   ├── 2_factor_calculate     # State after factor calculation (pickle)
    │   │   ├── 3_factor_backtest      # State after backtesting (pickle)
    │   │   └── 4_feedback             # State after feedback (pickle)
    │   └── 1/                         # Loop iteration 1
    │       └── ...
    ├── init/                          # Component initialization states
    │   ├── scenario/<pid>/            # QlibAlphaAgentScenario
    │   ├── hypothesis generator/<pid>/
    │   ├── experiment generation/<pid>/
    │   ├── coder/<pid>/
    │   ├── runner/<pid>/
    │   └── summarizer/<pid>/
    ├── r/                             # Research phase (Idea + Factor Agents)
    │   ├── hypothesis generation/<pid>/  # Hypothesis pickle files
    │   ├── experiment generation/<pid>/  # Factor expression pickle files
    │   └── llm_messages/<pid>/          # Full LLM conversation logs
    ├── d/                             # Development phase (CoSTEER coder)
    │   ├── evolving code/<pid>/         # Code evolution iterations (pickle)
    │   ├── evolving feedback/<pid>/     # Evaluation feedback per iteration (pickle)
    │   ├── coder result/<pid>/          # Final coder output (pickle)
    │   └── llm_messages/<pid>/          # Code review LLM conversations
    ├── ef/                            # Evaluate & Feedback phase
    │   ├── runner result/<pid>/         # Backtest results (pickle)
    │   ├── Quantitative Backtesting Chart/<pid>/  # Plotly chart objects (pickle)
    │   ├── feedback/<pid>/              # Eval Agent feedback (pickle)
    │   └── <pid>/common_logs.log        # Detailed metrics (IC, ICIR, Sharpe, etc.)
    └── llm_messages/                  # Top-level feedback LLM logs
        └── <pid>/common_logs.log
```

**Key Structure Details**:
- `<pid>` is a process identifier that remains consistent across the entire session
- Pickle files are named with timestamps: `YYYY-MM-DD_HH-MM-SS-microseconds.pkl`
- Each phase directory contains a `common_logs.log` file with human-readable logs
- `__session__/` stores cumulative snapshots for session resumption - each numbered directory (0, 1, 2...) represents one loop iteration with files for each pipeline step
- Multiple iterations are stored in the same phase directories (r/, d/, ef/), differentiated by file timestamps
- The `init/` directory captures the initialization state of all components when the session first starts

### 8.2 Agent Outputs

**Idea Agent (`r/hypothesis generation/<pid>/`)**:
- Serialized hypothesis objects stored as `.pkl` files (one per iteration)
- Each hypothesis pickle contains:
  - `hypothesis`: Market hypothesis text with theoretical grounding
  - `direction`: Keywords summarizing the hypothesis
  - `experiment_plan`: Suggested approaches for factor construction
  - `variables_to_use`: Recommended data fields (e.g., `["$close", "$volume"]`)
  - `reason`: Justification for the hypothesis
- Access these objects by unpickling them with Python's `pickle` module

**Factor Agent (`r/experiment generation/<pid>/`)**:
- Serialized factor experiment objects as `.pkl` files containing factor names, descriptions, and DSL expressions
- Each factor experiment pickle includes:
  - `sub_tasks`: List of factor tasks
  - For each task:
    - `factor_name`: Descriptive name (e.g., "Volume_Momentum_Cross")
    - `factor_description`: Explanation of the factor logic
    - `factor_formulation`: DSL expression (e.g., `Rank($volume) * Rank($close - Ref($close, 5))`)
    - `variables`: List of data fields used
- Timestamp-based filenames allow tracking factor evolution across iterations

**Coder / CoSTEER (`d/`)**:
- `d/evolving code/<pid>/`: Contains pickle files for each evolution iteration showing code refinement
- `d/evolving feedback/<pid>/`: Has corresponding feedback for each evolution step
- `d/coder result/<pid>/`: Contains the final validated result after all evolution iterations complete
- Each pickle file includes:
  - Python implementation of factor calculation
  - Execution logs and error messages (if any)
  - Computed factor values as pandas DataFrames
  - Debugging history showing syntax errors and fixes

**Runner + Eval Agent (`ef/`)**:
- `ef/runner result/<pid>/`: Complete backtest results stored as pickle files
  - Metrics: IC, ICIR, Rank IC, annual return, information ratio, max drawdown, Sharpe ratio
  - Separate metrics for train/validation/test periods
  - Performance comparison vs benchmark (SPX for US market)
- `ef/Quantitative Backtesting Chart/<pid>/`: Serialized Plotly figure objects showing PnL curves
  - Cumulative returns over train/val/test periods
  - Visual comparison against benchmark returns
- `ef/feedback/<pid>/`: Structured accept/reject feedback as pickle files
  - Decision: `accept` or `reject` with detailed reasoning
  - Specific issues identified (overfitting, low IC, etc.)
  - Suggestions for improvement in next iteration

**LLM Messages**:
- Each phase directory contains `llm_messages/<pid>/common_logs.log` with full prompt/response transcripts
- Shows the exact conversations between the system and LLM models
- Useful for debugging prompt engineering and understanding agent reasoning
- The top-level `llm_messages/` directory contains the Eval Agent's feedback conversation

**Metrics Logs**:
- Found in `ef/<pid>/common_logs.log` as human-readable text
- Includes detailed breakdowns of IC, ICIR, Rank IC, Sharpe ratio, drawdown, returns
- Also contains factor correlation analysis showing overlap with existing factors
- Each iteration appends new metrics to this log file

### 8.3 Key Performance Metrics

AlphaAgent evaluates factors using standard quantitative finance metrics:

| Metric | Description | Good Value | Interpretation |
|--------|-------------|------------|----------------|
| **IC** | Information Coefficient (Pearson correlation between factor values and forward returns) | > 0.03 | Measures predictive power; higher is better |
| **ICIR** | IC divided by its standard deviation | > 0.5 | Measures consistency of predictions; higher is better |
| **Rank IC** | Spearman rank correlation between factor values and forward returns | > 0.03 | Measures monotonic relationship; more robust to outliers than IC |
| **Annual Return** | Annualized portfolio return | > 15% | Absolute performance; compare to benchmark |
| **IR** | Information Ratio (excess return / tracking error) | > 1.0 | Risk-adjusted performance vs benchmark |
| **Max Drawdown** | Largest peak-to-trough decline | < 20% | Worst-case loss; lower is better |
| **Sharpe Ratio** | (Return - Risk-free rate) / volatility | > 1.5 | Risk-adjusted return; higher is better |

**Acceptance Thresholds** (defaults in AlphaAgent):
- **Minimum IC**: 0.02 (test set)
- **Minimum ICIR**: 0.3 (test set)
- **Overfitting check**: IC_test should be within 50% of IC_train

A factor is typically accepted if it meets all thresholds and shows no severe overfitting.

## Using the Monitoring UI

### Launch the Dashboard

```bash
alphaagent ui --port 19899 --log_dir log/
```

Open your browser to `http://localhost:19899` to view the interactive dashboard.

### Dashboard Overview

The Streamlit UI provides three main panels:

**Sidebar Navigation**:
- Session selector: Choose which run to view
- Loop iteration selector: Navigate through iterations
- Summary statistics: Overall success rate, average IC, best factors

**Main Panel Tabs**:

1. **Idea Agent Panel**:
   - Displays hypothesis cards for each iteration
   - Shows hypothesis text, keywords, and theoretical grounding
   - Links to detailed experiment plan

2. **Factor Agent Panel**:
   - Shows factor expression cards
   - Displays factor name, description, and DSL formulation
   - Highlights novelty score and complexity metrics
   - Color-coded by acceptance status (green = accepted, red = rejected)

3. **Eval Agent Panel**:
   - **PnL Charts**: Plotly interactive charts showing cumulative returns vs benchmark
     - Separate curves for train/validation/test periods
     - Hover to see exact dates and return values
     - Zoom and pan controls
   - **Metrics Table**: Comprehensive table with all performance metrics
     - IC, ICIR, Rank IC for train/val/test
     - Returns, Sharpe, max drawdown
     - Color-coded by threshold (green = pass, red = fail)
   - **Feedback Panel**: Eval Agent's detailed feedback
     - Accept/reject decision with reasoning
     - Specific issues identified (overfitting, low IC, etc.)
     - Suggestions for improvement

### Tips for Using the UI

- Use the **iteration slider** to compare hypotheses and factors across loops
- Check the **metrics heatmap** to quickly identify best-performing factors
- Review **feedback text** to understand why factors were rejected
- Export results using the download buttons (CSV for metrics, PNG for charts)

## Multi-Factor Backtesting

If you already have factor expressions and want to backtest them without running the full AlphaAgent loop, use the `backtest` command.

### Create Factor CSV File

Create a CSV file (e.g., `my_factors.csv`) with two columns:

```csv
factor_name,factor_expression
Momentum_5D,"Rank($close / Ref($close, 5) - 1)"
Volume_Surge,"Rank($volume / Mean($volume, 20))"
Price_Acceleration,"Rank(($close / Ref($close, 1)) / (Ref($close, 1) / Ref($close, 2)))"
Mean_Reversion_10D,"Rank(Mean($close, 10) / $close - 1)"
Volatility_Scaled_Return,"Rank(($close / Ref($close, 5) - 1) / Std($close, 20))"
```

### Run Backtest

```bash
alphaagent backtest --factor_path "my_factors.csv"
```

This will:
1. Load factor expressions from CSV
2. Calculate factor values across all stocks and dates
3. Run backtest using the same configuration as AlphaAgent
4. Generate performance report in `log/` directory

### Available Data Fields

Your factor expressions can use these base fields:

| Field | Description | Example Usage |
|-------|-------------|---------------|
| `$open` | Opening price | `$open / Ref($close, 1) - 1` |
| `$high` | Daily high price | `($high - $low) / $close` |
| `$low` | Daily low price | `Rank($low)` |
| `$close` | Closing price | `$close / Ref($close, 5) - 1` |
| `$volume` | Trading volume | `$volume / Mean($volume, 20)` |

For Chinese markets, additional fields are available: `$amount`, `$turn`, `$pettm`, `$pbmrq`.

### Factor DSL Function Categories

The factor expression language provides functions in several categories:

**Time-Series Functions** (operate within each stock's history):
- `Ref(x, n)`: Value n days ago
- `Delta(x, n)`: Difference from n days ago
- `TS_Rank(x, n)`: Percentile rank over n days
- `TS_Max(x, n)`, `TS_Min(x, n)`, `TS_Mean(x, n)`, `TS_Sum(x, n)`: Rolling aggregations
- `TS_Std(x, n)`: Rolling standard deviation

**Cross-Sectional Functions** (operate across all stocks at each date):
- `Rank(x)`: Percentile rank across stocks
- `Mean(x)`, `Median(x)`, `Std(x)`: Cross-sectional aggregations
- `Max(x)`, `Min(x)`: Cross-sectional extremes
- `Skew(x)`, `Kurt(x)`: Higher-order moments

**Technical Indicators**:
- `MACD(x)`: Moving Average Convergence Divergence
- `RSI(x, n)`: Relative Strength Index
- `BBANDS(x, n)`: Bollinger Bands
- `ATR(n)`: Average True Range
- `OBV(x)`: On-Balance Volume

**Mathematical Functions**:
- `Abs(x)`, `Sign(x)`, `Log(x)`, `Power(x, n)`
- `Max(x, y)`, `Min(x, y)`: Element-wise min/max
- `If(condition, true_val, false_val)`: Conditional expression

**Regression Functions**:
- `Slope(y, x, n)`: Linear regression slope over n days
- `Corr(x, y, n)`: Rolling correlation
- `Cov(x, y, n)`: Rolling covariance

For the complete function library, see `alphaagent/components/coder/factor_coder/function_lib.py`.

## Customizing Backtest Settings

### Configuration File Locations

Backtest behavior is controlled by YAML configuration files:

- **Baseline (single factors)**: `alphaagent/scenarios/qlib/experiment/factor_template/conf.yaml`
- **Combined (multiple factors)**: `alphaagent/scenarios/qlib/experiment/factor_template/conf_us_combined_kdd_ver.yaml` (US) or `conf_cn_combined_kdd_ver.yaml` (CN)

### Time Period Configuration

Edit the `segments` section in the config file to change train/validation/test splits:

```yaml
segments:
    train: [2015-01-01, 2019-12-31]  # Training period (5 years)
    valid: [2020-01-01, 2020-12-31]  # Validation period (1 year)
    test: [2021-01-01, 2024-12-30]   # Test period (4 years)
```

**Important**: After changing time periods, you must clear cache:
```bash
rm -rf ./git_ignore_folder/*
rm -rf ./pickle_cache/*
rm -f alphaagent/scenarios/qlib/experiment/factor_data_template/daily_pv_all.h5
rm -f alphaagent/scenarios/qlib/experiment/factor_data_template/daily_pv_debug.h5
```

### Portfolio Strategy Parameters

The `port_analysis_config` section controls portfolio simulation:

```yaml
port_analysis_config:
    strategy:
        class: TopkDropoutStrategy
        module_path: qlib.contrib.strategy
        kwargs:
            signal: <PRED>           # Use model predictions as signal
            topk: 50                 # Buy top 50 stocks by predicted return
            n_drop: 5                # Drop bottom 5 positions daily (risk control)
    backtest:
        start_time: 2021-01-01
        end_time: 2024-12-30
        account: 100000000           # Starting capital ($100M)
        benchmark: SPX               # S&P 500 index for comparison
        exchange_kwargs:
            limit_threshold: 0.095   # Max daily price change (9.5%)
            deal_price: open         # Execute at open price
            open_cost: 0.0           # No commission on buy
            close_cost: 0.0005       # 5 bps commission on sell
            min_cost: 0              # No minimum commission
```

**Key parameters to adjust**:
- `topk`: Number of stocks to hold (higher = more diversified, lower = more concentrated)
- `n_drop`: Daily dropout for risk control (prevents holding losers too long)
- `account`: Starting capital (doesn't affect IC/ICIR, but affects absolute PnL charts)
- `open_cost` / `close_cost`: Transaction costs (use realistic values for your broker)

### Model Parameters

AlphaAgent uses LightGBM by default. You can switch to XGBoost or tune hyperparameters:

**LightGBM** (default):
```yaml
model:
    class: LGBModel
    module_path: qlib.contrib.model.gbdt
    kwargs:
        loss: mse
        colsample_bytree: 0.8879
        learning_rate: 0.1
        subsample: 0.8789
        lambda_l1: 205.6999
        lambda_l2: 580.9768
        max_depth: 3              # Lower = less overfitting
        num_leaves: 210
        num_threads: 20
```

**XGBoost** (alternative):
```yaml
model:
    class: XGBModel
    module_path: qlib.contrib.model.xgboost
    kwargs:
        eval_metric: rmse
        colsample_bytree: 0.8879
        eta: 0.0421
        max_depth: 8
        n_estimators: 647
        subsample: 0.8789
        nthread: 20
```

**Always clear cache** after changing model parameters:
```bash
rm -rf ./pickle_cache/*
```

## Troubleshooting

### Installation Issues

| Problem | Solution |
|---------|----------|
| `alphaagent: command not found` | Activate virtual environment: `source .venv/bin/activate` |
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ModuleNotFoundError: No module named 'qlib'` | Install Qlib: `cd qlib && uv pip install . && cd ..` |
| `Python version mismatch` | Create venv with correct version: `uv venv --python 3.10` |
| Permission denied errors | Check file permissions: `chmod +x alphaagent/scripts/*` |

### Data Issues

| Problem | Solution |
|---------|----------|
| `FileNotFoundError: ~/.qlib/qlib_data/us_data` | Download data: `cd qlib && python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us` |
| `No data available for date range` | Check data coverage: `python -c "import qlib; qlib.init(provider_uri='~/.qlib/qlib_data/us_data'); from qlib.data import D; print(D.calendar())"` |
| Outdated data | Re-download: `rm -rf ~/.qlib/qlib_data/us_data && cd qlib && python scripts/get_data.py ...` |
| Wrong market data being used | Verify `conf.yaml` lines 1-13 and `generate.py` line 3 are set to US |

### LLM API Issues

| Problem | Solution |
|---------|----------|
| `AuthenticationError: Invalid API key` | Check `.env` file has correct `OPENAI_API_KEY` |
| `Connection timeout` | Increase `RETRY_WAIT_SECONDS` in `.env`, check network/firewall |
| `Rate limit exceeded` | Reduce concurrency, wait and retry, or upgrade API plan |
| `Model not found` | Verify `REASONING_MODEL` and `CHAT_MODEL` names are correct for your API provider |
| API calls timing out | Increase `MAX_RETRY` to 10 in `.env` |

### Runtime Issues

| Problem | Solution |
|---------|----------|
| `FactorEmptyError: Factor extraction failed` | This is handled gracefully; the loop continues to the next iteration. Check `log/` for details on which factors failed. |
| Process killed after 3 hours | This is expected behavior (timeout). Increase `FACTOR_MINING_TIMEOUT` in `.env` or resume session: `alphaagent mine --path log/<timestamp>/` |
| Out of memory error | Reduce `topk` in config (fewer stocks = less memory), or use a machine with more RAM |
| Stale backtest results | Clear caches: `rm -rf ./pickle_cache/* ./git_ignore_folder/*` |
| `signal.SIGALRM not found` (Windows) | Use WSL (Windows Subsystem for Linux) or a Linux/macOS machine |
| Docker-related errors | Ensure `USE_LOCAL=True` in `.env` to bypass Docker entirely |

### Performance Issues

| Problem | Solution |
|---------|----------|
| Very low IC/ICIR (<0.01) | Try different hypotheses; some market regimes are harder to predict |
| High overfitting (train IC >> test IC) | Reduce `max_depth` in model config, increase regularization |
| Factors always rejected | Lower acceptance thresholds in `alphaagent/components/coder/factor_coder/evaluators.py` (advanced) |
| Slow iteration speed | Use faster models (DeepSeek vs OpenAI), reduce `topk`, use `USE_LOCAL=True` |

## Glossary

- **Alpha**: Excess return of an investment relative to a benchmark index. In factor investing, refers to the predictive signal provided by a factor.

- **Alpha Decay**: The phenomenon where a discovered alpha factor loses its predictive power over time due to market changes, overcrowding, or overfitting.

- **Alpha Factor**: A quantitative formula that assigns a score to each stock, intended to predict future returns. Example: `Rank($volume / Mean($volume, 20))`.

- **Backtest**: Simulation of a trading strategy using historical data to evaluate performance before deploying real capital.

- **DSL (Domain-Specific Language)**: The specialized syntax used to express factor formulas in AlphaAgent (e.g., `Ref()`, `Rank()`, `Mean()`).

- **Factor Zoo**: The problem of having thousands of published factors in academic literature, many of which don't work out-of-sample or are redundant.

- **IC (Information Coefficient)**: Pearson correlation between factor values and forward returns at each time step, averaged over time. Measures linear predictive power.

- **ICIR (Information Coefficient Information Ratio)**: IC divided by its standard deviation. Measures consistency of factor predictions.

- **Information Ratio**: Risk-adjusted performance metric calculated as (portfolio return - benchmark return) / tracking error. Higher values indicate better risk-adjusted excess returns.

- **LightGBM**: Gradient boosting framework used to train models on factor values. Known for speed and accuracy with tabular data.

- **Max Drawdown**: The largest peak-to-trough decline in portfolio value during the backtest period. Measures worst-case loss.

- **Qlib**: Microsoft's open-source quantitative investment platform that AlphaAgent uses for data management and backtesting.

- **Rank IC**: Spearman rank correlation between factor values and forward returns. More robust to outliers than IC.

- **Regularization**: Techniques to prevent overfitting, including complexity penalties and novelty checks in AlphaAgent's factor generation.

- **TopkDropoutStrategy**: Portfolio construction method that buys the top k stocks by predicted return and daily drops the worst n_drop performers.

- **CSI500**: China Securities Index 500, a stock market index of 500 stocks traded on Shanghai and Shenzhen exchanges.

- **S&P 500 (SPX)**: Standard & Poor's 500 Index, a stock market index tracking 500 large US companies.

## Next Steps

Congratulations! You now have AlphaAgent running and understand its core concepts. Here are suggested next steps:

### Deepen Your Understanding

- **Read the research paper**: `alphaagent-paper.pdf` provides theoretical foundations, empirical results, and detailed explanations of the regularization mechanisms.

- **Explore RD-Agent**: AlphaAgent is built on the [RD-Agent framework](https://github.com/microsoft/RD-Agent). Understanding RD-Agent will help you customize AlphaAgent's workflow.

- **Study the factor library**: Review `alphaagent/components/coder/factor_coder/function_lib.py` to see all available DSL functions and their implementations.

- **Examine generated factors**: Open the log files from your runs to see actual hypotheses, factor expressions, and feedback. This will give you intuition for what works.

### Experiment and Customize

- **Try different hypotheses**: Experiment with various market phenomena (seasonality, liquidity, earnings momentum, etc.)

- **Build a factor library**: Collect accepted factors from multiple runs and backtest them together using `alphaagent backtest`

- **Tune hyperparameters**: Adjust model parameters, portfolio strategy settings, and acceptance thresholds

- **Add custom functions**: Extend `function_lib.py` with domain-specific technical indicators

### Advanced Topics

- **Knowledge base management**: AlphaAgent maintains a RAG-based knowledge base of accepted factors. Explore `alphaagent/core/knowledge_base.py` to customize retrieval and novelty detection.

- **Multi-market strategies**: Run AlphaAgent on both US and CN markets, then combine factors for international portfolios

- **Production deployment**: Integrate AlphaAgent factors into a live trading system (requires additional infrastructure for data feeds, execution, risk management)

- **Developer documentation**: See `CLAUDE.md` for detailed architecture documentation, development workflows, and contribution guidelines

### Get Help and Contribute

- **GitHub Issues**: Report bugs or request features at the project repository

- **Community**: Join discussions with other AlphaAgent users to share strategies and insights

- **Cite the research**: If you use AlphaAgent in academic work, please cite the KDD 2025 paper (see README.md for BibTeX)

Happy factor mining!
