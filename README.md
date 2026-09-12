# Earnings Call Alpha: Segment-Level Sentiment as a Trading Signal

**Question:** Does sentiment measured at the *segment* level of an earnings call (per Q&A exchange, per prepared-remarks topic) predict short-horizon stock returns better than whole-transcript sentiment?

This is a reproduction-and-extension of two 2024/2025 papers:

- Kim et al., *"Can AI Read Between the Lines? Benchmarking LLMs on Financial Nuance"* (arXiv:2505.16090) — finds that segment-level sentiment on earnings calls carries information that whole-transcript sentiment averages away (e.g. a company's core-segment tone can diverge sharply from its overall tone).
- Related idea from Kim et al., *"DeFine: Decision-Making with Analogical Reasoning over Factor Profiles"* (arXiv:2410.01772) — structuring call content into discrete "factor profiles" instead of one blended score.

## Why this project

Most quant-side portfolios show price-only signals; most IB-side portfolios show no statistical validation. This project sits in between: it takes a qualitative, IB-style artifact (an earnings call) and asks a falsifiable, quant-style question about it — with an explicit backtest, transaction costs, and multiple-testing discipline, not just a headline accuracy number.

## Hypothesis (falsifiable, stated up front)

H1: The dispersion of sentiment across call segments (max − min segment sentiment, and specifically the sentiment of the segment covering the company's largest/most-discussed business line) has incremental predictive power for the 1-day and 3-day abnormal return around the call, beyond what whole-transcript sentiment alone explains.

Null result is a legitimate and reportable outcome here — the project is designed so that "H1 doesn't survive out-of-sample" is still a complete, defensible finding.

## Data (all free / public — no WRDS/CRSP/Compustat)

- **Transcripts:** small curated sample (~25-40 calls, 8-10 large-cap tickers across sectors), sourced from SEC EDGAR 8-K Exhibit 99.1/99.2 press releases and issuer-published IR transcripts (first-party publication by the company itself — avoids third-party scraping ToS issues). See `docs/data_sources.md` for the exact list and provenance of every transcript used.
- **Prices:** daily OHLCV via `yfinance` (Yahoo Finance) for event-window return calculation.
- **Benchmark factors:** Kenneth French Data Library (Fama-French 3/5-factor + momentum) for abnormal-return (alpha) calculation instead of raw returns.
- **Filings context:** SEC EDGAR full-text search / XBRL API for point-in-time fundamentals (to avoid restated-data lookahead bias).

## Method

1. **Segment the call**: split into prepared-remarks topic blocks + individual analyst Q&A exchanges (question + answer as one segment).
2. **Score each segment**: FinBERT (finance-domain sentiment classifier) per segment. See `docs/methodology.md` for why FinBERT was chosen over a general-purpose LLM as the primary scorer (reproducibility, cost, determinism) and where an LLM-based comparison is used as a secondary check.
3. **Compute dispersion features**: whole-transcript sentiment (baseline), max/min segment sentiment, dispersion, and a "core segment" sentiment where the core segment is identified by keyword/topic matching to the firm's largest reported revenue segment (from the 10-K).
4. **Event-window returns**: abnormal return vs. Fama-French benchmark for [0,+1] and [0,+3] trading days after the call.
5. **Statistical test**: does segment dispersion add explanatory power over whole-transcript sentiment (nested regression / information coefficient comparison)? Report with multiple-testing correction (this is a small-N study — say so honestly).
6. **Backtest**: simple long/short portfolio sorted on the dispersion signal, walk-forward, with realistic transaction cost assumptions and turnover reporting, scored with the Probabilistic Sharpe Ratio (Bailey & Lopez de Prado, 2012) rather than a raw Sharpe ratio. This is illustrative given small N, not a claim of a deployable strategy — the report says this explicitly.

## Project status

Early build — see `docs/plan.md` for the phased build plan and current progress.

## Structure

```
data/raw/transcripts/   curated transcript sources + provenance
data/raw/prices/        cached price data
data/processed/         segment-level sentiment scores, feature tables
src/data/               EDGAR + price fetching
src/nlp/                segmentation + FinBERT scoring
src/backtest/           event-study + long/short backtest
src/viz/                dashboard / plots
notebooks/              exploratory analysis, the "story" walkthrough
docs/                   data provenance, methodology, limitations
```

## Limitations (stated up front, not buried)

- Small sample size (~25-40 calls) — this is a research prototype, not a production signal. Statistical power is limited and this is disclosed in all result reporting.
- Transcript sourcing is manual/curated rather than a full historical database, so ticker/period coverage is intentionally narrow rather than broad-and-noisy.
- No intraday data — event-window returns use daily closes, which is a coarser measurement than the sub-minute reaction studied in some HFT-adjacent literature.
