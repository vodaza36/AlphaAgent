---
description: Research scientific literature on alpha factors and generate a novel market hypothesis for AlphaAgent mining
argument-hint: "[optional: research focus like 'volatility clustering' or 'momentum reversal']"
allowed-tools: WebSearch, WebFetch, Read, Write, Glob, Grep, Bash
---

# Research Hypothesis Command

You are tasked with researching scientific literature on quantitative alpha factors and synthesizing a novel, testable market hypothesis for AlphaAgent factor mining. This command automates the hypothesis generation phase by grounding ideas in recent academic research while ensuring diversity across runs.

## Step 1: Load State

First, load the three JSON state files that track research history:

1. **`.claude/research/hypotheses.json`** — Previously generated hypotheses
2. **`.claude/research/resources.json`** — Resource registry with extraction tracking
3. **`.claude/research/blacklist.json`** — Exhausted or unhelpful resource URLs

**Schema for hypotheses.json:**
```json
{
  "version": 1,
  "hypotheses": [
    {
      "id": "h_YYYYMMDD_NNN",
      "hypothesis": "Full hypothesis text grounded in research",
      "direction_string": "Concise string for --direction CLI arg",
      "source_urls": ["https://arxiv.org/abs/..."],
      "source_titles": ["Paper Title"],
      "research_theme": "volatility-volume",
      "suggested_factors": ["RANK(TS_STD($close, 10))"],
      "status": "unused",
      "created_at": "2026-02-07T10:30:00Z"
    }
  ]
}
```

**Schema for resources.json:**
```json
{
  "version": 1,
  "resources": [
    {
      "url": "https://arxiv.org/abs/...",
      "title": "Paper Title",
      "source_type": "arxiv",
      "extraction_count": 1,
      "max_extractions": 3,
      "themes_extracted": ["volatility-volume"],
      "first_seen": "2026-02-07T10:30:00Z",
      "last_accessed": "2026-02-07T10:30:00Z"
    }
  ]
}
```

**Schema for blacklist.json:**
```json
{
  "version": 1,
  "blacklisted": [
    {
      "url": "https://example.com/paywalled",
      "reason": "paywalled_no_abstract",
      "added_at": "2026-02-07T10:30:00Z"
    }
  ]
}
```

**Blacklist reasons:** `exhausted`, `paywalled_no_abstract`, `low_quality`, `irrelevant`, `duplicate_content`

**If the directory or files don't exist:**
- Create `.claude/research/` directory using Bash (`mkdir -p .claude/research`)
- Initialize each JSON file with the empty structure above using Write tool

**If files are corrupted (invalid JSON):**
- Back up as `.bak` (e.g., `hypotheses.json.bak`)
- Create fresh files with empty structure

## Step 2: Determine Research Direction

**If `$ARGUMENTS` provided** (e.g., `/research-hypothesis volatility clustering`):
- Use it as the primary research focus
- Add related keywords to expand the search (e.g., "volatility clustering" → "volatility persistence", "GARCH", "realized volatility")

**If no arguments provided:**
- Analyze existing hypotheses from `hypotheses.json` to identify underexplored themes
- Choose from the **diversity palette**: momentum/trend, mean reversion, volatility/risk, volume/liquidity, cross-sectional, technical patterns, regime change, order flow
- Prioritize themes with fewer existing hypotheses to ensure diversity
- If all themes are equally explored, pick the theme with the oldest last-generated hypothesis

**Output:** A focused research direction with 2-3 search query variations

## Step 3: Web Research

Execute systematic web research to find relevant academic literature:

### Search Sources (prioritized):
1. **arXiv** (preprints, most recent research)
2. **SSRN** (finance-focused working papers)
3. **Google Scholar** (peer-reviewed publications)
4. **Quantitative finance blogs** (AQR Insights, Alpha Architect, QuantConnect, QuantPedia)

### Search Queries (adapt to research direction):
- `"alpha factor" equity stock site:arxiv.org 2025 2026`
- `quantitative factor investing alpha decay SSRN`
- `cross-sectional equity factors predictive power`
- `[research direction] stock prediction machine learning`
- `market microstructure [research direction] trading`

### Research Protocol:
1. Use WebSearch for each query variation (2-3 queries minimum)
2. Filter results against:
   - **Blacklisted URLs** from `blacklist.json`
   - **Exhausted resources** (resources where `extraction_count >= max_extractions`)
3. Select 2-4 promising results based on:
   - Publication date (prefer 2024-2026)
   - Relevance to research direction
   - Source credibility (peer-reviewed > preprints > blogs)
4. Use WebFetch to extract key findings from each selected resource
   - **Prompt for WebFetch:** "Extract the main hypothesis, methodology, key findings, and any novel factor construction techniques from this paper. Focus on actionable insights for quantitative factor design."
5. If WebFetch fails (paywall, 404, etc.):
   - Add URL to `blacklist.json` with appropriate reason
   - Try the next result

### Handling Edge Cases:
- **All resources exhausted for theme:** Broaden search terms or switch to adjacent theme
- **No search results:** Try alternative query formulations or consult well-known repositories (e.g., `site:papers.ssrn.com "factor investing"`)
- **Paywalls:** Extract information from abstracts only; if insufficient, blacklist and move on

## Step 4: Synthesize Hypothesis

Based on research findings, construct a novel hypothesis that:

### Grounding Requirements:
1. **Cite specific findings** from 2-3 papers
   - Example: "Drawing on Zhang et al. (2025) who found that volatility clustering predicts momentum reversals..."
2. **Map to available DSL functions** from `alphaagent/scenarios/qlib/prompts_alphaagent.yaml` (lines 47-128)
   - Available functions include: RANK, ZSCORE, TS_CORR, TS_STD, MACD, RSI, REGRESI, EMA, etc.
3. **Use only available variables:** `$open`, `$close`, `$high`, `$low`, `$volume`, `$return`
4. **Ensure testability** with Chinese stock market data (daily frequency, 2010-present typical range)

### Hypothesis Structure:
- **Full hypothesis** (2-4 sentences): Theoretical foundation, market mechanism, expected signal
- **Direction string** (1-2 sentences): Concise, actionable version for CLI `--direction` argument
- **Suggested factors** (2-3 expressions): Concrete implementations using DSL syntax

### Example Output:
```
**Full hypothesis:**
Recent research on volatility clustering (Zhang et al., 2025) demonstrates that periods of high volatility persistence predict short-term momentum reversals in equity markets. This occurs because volatility shocks trigger risk-off behavior, causing temporary mispricings that revert as uncertainty subsides. Combining volatility measures with volume dynamics can identify these reversal points more precisely.

**Direction string:**
"Stocks exhibiting high volatility persistence combined with abnormal volume spikes experience short-term mean reversion as market participants overreact to uncertainty shocks."

**Suggested factors:**
1. `RANK(TS_STD($close, 10) / TS_STD($close, 60))` — Volatility regime shift
2. `TS_CORR($volume, TS_STD($close, 5), 20)` — Volume-volatility relationship
3. `REGRESI($return, TS_STD($close, 10), 20)` — Return residual after volatility adjustment
```

## Step 5: Deduplicate Against Existing Hypotheses

Compare the new hypothesis against all entries in `hypotheses.json`:

### Similarity Checks:
1. **Research theme:** Is the theme identical or highly overlapping?
2. **Semantic similarity:** Do the hypotheses test the same market mechanism?
3. **Factor similarity:** Are suggested factors structurally similar?

### Deduplication Logic:
- **If high similarity detected (>70% match):**
  - Refine the hypothesis to emphasize a different aspect
  - OR pivot to a different sub-theme within the research direction
  - OR add a novel constraint or condition
- **If medium similarity (40-70%):**
  - Acceptable if the mechanism differs or uses different factor construction techniques
- **If low similarity (<40%):**
  - Proceed to Step 6

### Example Refinement:
- **Original (similar to existing):** "High volatility predicts momentum reversals"
- **Refined:** "Asymmetric volatility (downside vs upside) predicts directional reversals, with stronger effects during high-volume regimes"

## Step 6: Update State Files

Update all three state files with the new research session:

### Update `hypotheses.json`:
- Generate unique ID: `h_YYYYMMDD_NNN` (e.g., `h_20260207_001`)
- Set `status: "unused"` (will be updated to "used" when mining starts)
- Add `created_at` timestamp in ISO 8601 format

### Update `resources.json`:
- For each accessed resource:
  - If new: Add entry with `extraction_count: 1`, `first_seen` and `last_accessed` timestamps
  - If existing: Increment `extraction_count`, update `last_accessed`, append new theme to `themes_extracted` if not already present
- If `extraction_count >= max_extractions` (default: 3), move to blacklist

### Update `blacklist.json`:
- Add any paywalled, irrelevant, or failed resources encountered during WebFetch
- Include reason and timestamp

### Write Operations:
- Use Write tool to save updated JSON files
- Ensure proper JSON formatting (use Python's `json.dumps` logic mentally)

## Step 7: Present Results to User

Output the final hypothesis in a ready-to-use format:

```markdown
## Research Hypothesis Generated

**Direction** (copy-paste ready for CLI):
```bash
alphaagent mine --direction "Stocks exhibiting high volatility persistence combined with abnormal volume spikes experience short-term mean reversion as market participants overreact to uncertainty shocks."
```

**Full hypothesis:**
Recent research on volatility clustering (Zhang et al., 2025) demonstrates that periods of high volatility persistence predict short-term momentum reversals in equity markets. This occurs because volatility shocks trigger risk-off behavior, causing temporary mispricings that revert as uncertainty subsides. Combining volatility measures with volume dynamics can identify these reversal points more precisely.

**Research theme:** `volatility-volume-reversal`

**Sources:**
- [Volatility Clustering and Momentum Reversals in Equity Markets](https://arxiv.org/abs/2501.12345) (Zhang et al., 2025) — Found that volatility persistence predicts short-term reversals
- [Volume Shocks and Price Discovery](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4567890) (Chen & Li, 2024) — Volume spikes during volatility shocks indicate overreaction

**Suggested factors:**
1. `RANK(TS_STD($close, 10) / TS_STD($close, 60))` — Volatility regime shift indicator
2. `TS_CORR($volume, TS_STD($close, 5), 20)` — Volume-volatility coupling strength
3. `REGRESI($return, TS_STD($close, 10), 20)` — Return residual after volatility adjustment

**Hypothesis ID:** `h_20260207_001` (saved to `.claude/research/hypotheses.json`)
```

## Additional Guidelines

### Function Reference:
Consult `alphaagent/scenarios/qlib/prompts_alphaagent.yaml` lines 47-128 for complete DSL function library. Key categories:
- **Cross-sectional:** RANK, ZSCORE, MEAN, STD, MAX, MIN
- **Time-series:** TS_MEAN, TS_STD, TS_CORR, TS_RANK, DELTA, DELAY
- **Technical indicators:** RSI, MACD, BB_UPPER, BB_LOWER
- **Regression:** REGBETA, REGRESI (with SEQUENCE for trend)
- **Smoothing:** EMA, SMA, WMA, DECAYLINEAR

### Variable Reference:
Only these variables are available in the Qlib data:
- `$open`, `$close`, `$high`, `$low`, `$volume`, `$return`

### Quality Criteria for Hypotheses:
1. **Specificity:** Avoid vague statements like "technical indicators predict returns"
2. **Mechanism:** Explain WHY the relationship exists (behavioral finance, market microstructure, etc.)
3. **Testability:** Can be implemented with 2-3 factor expressions using available DSL
4. **Novelty:** Not a trivial restatement of well-known effects (e.g., "momentum exists")
5. **Grounding:** Explicitly references 2+ research papers with specific findings

### State File Maintenance:
- **Max extractions per resource:** 3 (prevents over-reliance on single papers)
- **Blacklist automatically:** Resources with `extraction_count >= 3` or failed WebFetch
- **Backup on corruption:** Save `.bak` before recreating
- **Version field:** Always set to `1` for current schema

### Error Recovery:
- **WebSearch returns no results:** Try broader queries, check date filters
- **WebFetch fails on all results:** Fall back to known repositories (AQR, Alpha Architect blog posts)
- **Cannot generate novel hypothesis:** Relax similarity threshold or pick orthogonal theme
- **State file write fails:** Check permissions, disk space; report error to user

## Execution Checklist

Before presenting results, verify:
- [ ] State files loaded successfully (or created if first run)
- [ ] At least 2 web searches executed
- [ ] At least 2 resources successfully fetched
- [ ] Hypothesis grounded in specific research findings
- [ ] All suggested factors use valid DSL syntax
- [ ] All suggested factors use only available variables
- [ ] Hypothesis deduplicated against existing entries
- [ ] All state files updated and saved
- [ ] Output formatted for easy copy-paste to CLI

---

**Now execute this workflow based on the user's `$ARGUMENTS` (if provided) or automatically determine the research direction from existing state.**
