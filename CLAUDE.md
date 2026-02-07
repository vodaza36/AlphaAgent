# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlphaAgent is an autonomous framework for mining interpretable and decay-resistant alpha factors using LLM agents. It integrates three specialized agents (Idea Agent, Factor Agent, and Eval Agent) to propose market hypotheses, construct factors, and validate them through backtesting. The project is built on top of the Qlib quantitative investment framework and follows the RD-Agent architecture pattern. The scientific research paper alphaagent-paper.pdf describes the entire framework, that means is something is not clear always refer to the paper for more details.

## Development Environment Setup

### Initial Setup
```bash
# Create virtual environment with Python 3.10
uv venv --python 3.10

# Activate the environment
source .venv/bin/activate

# Install the package in editable mode
uv pip install -e .
```

### Data Preparation
The project requires Chinese stock data via Qlib:
```bash
# Clone and install Qlib
git clone https://github.com/microsoft/qlib.git
cd qlib
uv pip install .
cd ..

# Download stock data from baostock
python prepare_cn_data.py

# Convert data to Qlib format
cd qlib
python scripts/dump_bin.py dump_all \
  --include_fields open,high,low,close,preclose,volume,amount,turn,factor \
  --csv_path ~/.qlib/qlib_data/cn_data/raw_data_now \
  --qlib_dir ~/.qlib/qlib_data/cn_data \
  --date_field_name date \
  --symbol_field_name code

# Collect calendar data
python scripts/data_collector/future_calendar_collector.py --qlib_dir ~/.qlib/qlib_data/cn_data/ --region cn

# Download stock universe (CSI500/CSI300/CSI100)
python scripts/data_collector/cn_index/collector.py --index_name CSI500 --qlib_dir ~/.qlib/qlib_data/cn_data/ --method parse_instruments
```

### Configuration
Copy `.env.example` to `.env` and configure:
- `OPENAI_BASE_URL` and `OPENAI_API_KEY`: API endpoint and key
- `REASONING_MODEL`: Slow-thinking model for Idea and Factor agents (e.g., o3-mini, deepseek-reasoner)
- `CHAT_MODEL`: Model for debugging and feedback (e.g., deepseek-v3)
- `USE_LOCAL=True`: Run backtesting locally instead of Docker

## Common Commands

### Run AlphaAgent
```bash
# Start factor mining with market hypothesis
alphaagent mine --potential_direction "<YOUR_MARKET_HYPOTHESIS>"

# Alternative command
dotenv run -- python alphaagent/app/qlib_rd_loop/factor_mining.py --direction "<YOUR_MARKET_HYPOTHESIS>"
```

### Multi-Factor Backtesting
```bash
# Run backtest on factors from CSV file
alphaagent backtest --factor_path "<PATH_TO_CSV_FILE>"

# CSV format:
# factor_name,factor_expression
# MACD_Factor,"MACD($close)"
# RSI_Factor,"RSI($close)"
```

### Monitor Results
```bash
# Launch Streamlit UI to view logs
alphaagent ui --port 19899 --log_dir log/
```

### Clear Cache
When updating backtest configurations or rerunning baseline results:
```bash
rm -r ./pickle_cache/*
rm -r ./git_ignore_folder/*
```

### Development Tools
```bash
# Run linting
make lint              # Check all linters (mypy, ruff, isort, black, toml-sort)
make auto-lint         # Auto-fix with all linters

# Run tests
make test              # Run tests with coverage (requires ≥20% coverage)
make test-offline      # Run tests without API calls

# Build package
make build             # Build distribution package
```

## Architecture

### Core Framework (alphaagent/core/)
The project follows an evolutionary framework pattern:

- **evolving_framework.py**: Defines the base evolution strategy with `EvolvableSubjects`, `EvolvingStrategy`, and `RAGStrategy` for knowledge-based evolution
- **scenario.py**: Defines experiment scenarios (Qlib backtesting framework integration)
- **developer.py**: Implements `Developer` interface for code generation and execution
- **proposal.py**: Defines `Hypothesis`, `HypothesisGen`, `Hypothesis2Experiment`, and feedback mechanisms
- **experiment.py**: Manages experiment execution with `FBWorkspace` for code execution sandboxes
- **knowledge_base.py**: Knowledge management for RAG-based factor generation

### Agent Workflow (alphaagent/components/workflow/)
The main loop is implemented in `AlphaAgentLoop`:

1. **factor_propose**: Idea Agent generates market hypotheses
2. **factor_experiment**: Factor Agent constructs factors from hypotheses
3. **factor_implement**: Implements and parses factor expressions
4. **factor_evaluate**: Runner executes backtesting
5. **factor_feedback**: Eval Agent validates and provides feedback

The loop continues iteratively, refining factors based on feedback.

### Qlib Integration (alphaagent/scenarios/qlib/)
Qlib-specific implementations:

- **developer/factor_coder.py**: Factor code generation using CoSTEER framework
- **developer/factor_runner.py**: Executes factor backtesting via Qlib
- **developer/feedback.py**: Generates feedback from backtest results
- **proposal/factor_proposal.py**: Hypothesis generation and factor expression creation
- **experiment/factor_experiment.py**: Qlib scenario configuration and experiment management

### Factor Implementation (alphaagent/components/coder/factor_coder/)
Factor-specific logic:

- **factor.py**: `FactorTask` and `FactorFBWorkspace` for factor execution
- **evaluators.py**: Evaluation metrics and feedback generation
- **evolving_strategy.py**: Factor evolution strategies with regularization to prevent alpha decay
- **expr_parser.py**: Factor expression parsing and AST manipulation
- **factor_ast.py**: Abstract syntax tree representation for factors
- **function_lib.py**: Library of technical indicator functions

### Configuration System (alphaagent/app/qlib_rd_loop/conf.py)
Settings classes define different workflows:

- `AlphaAgentFactorBasePropSetting`: Main AlphaAgent workflow with three-agent system
- `FactorBackTestBasePropSetting`: Simple backtesting without hypothesis generation
- `ModelBasePropSetting`: Model training workflow (alternative to factor mining)

Each setting specifies:
- Scenario class
- Hypothesis generator
- Coder implementation
- Runner for execution
- Summarizer for feedback

### Logging and UI (alphaagent/log/)
Comprehensive logging system:

- **storage.py**: Persistent storage for experiment traces
- **ui/app.py**: Streamlit-based UI for visualizing results
- **ui/qlib_report_figure.py**: Plotly charts for backtest performance
- All agent interactions, factor expressions, and backtest results are logged

## Important Patterns

### Factor Expression Format
Factors are expressed using Qlib's expression language:
- Use `$` prefix for features (e.g., `$close`, `$volume`)
- Functions are called directly (e.g., `Mean($close, 5)`, `Ref($close, 1)`)
- See `function_lib.py` for available technical indicators

### Backtest Configuration Files
Located in `alphaagent/scenarios/qlib/experiment/`:
- **factor_template/conf.yaml**: Baseline configuration
- **factor_template/conf_cn_combined.yaml**: Configuration for newly proposed factors

To change train/val/test periods, delete cache in `./git_ignore_folder`, `./pickle_cache`, and remove `daily_pv_all.h5` and `daily_pv_debug.h5` in `factor_data_template/`.

### Local vs Docker Execution
Set `USE_LOCAL=True` in `.env` to run backtesting locally. This is faster and avoids Docker overhead. The `use_local` flag is passed through the workflow and determines execution environment.

### Session Management
The workflow supports session persistence:
- Sessions are saved to log directories
- Resume sessions using the `--path` parameter with session directory
- Useful for continuing long-running factor mining jobs

### Stop Event Handling
The workflow includes graceful shutdown via `stop_event`:
- Threads can be stopped cleanly
- Progress is preserved for resumption
- Implemented in `alphaagent_loop.py` with `@stop_event_check` decorator

## Testing

No dedicated test directory found. The project uses pytest with coverage requirements:
- Minimum 20% coverage (target is 80%)
- Offline tests available with `-m "offline"` marker
- Tests ignore `test/scripts` directory

## Citation
This project is based on research published at KDD 2025. When making significant changes, maintain attribution to the original AlphaAgent and RD-Agent frameworks.
