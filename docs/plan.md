# Build Plan

## Phase 0 — Setup
- [x] Repo structure
- [x] Python env (torch + transformers + FinBERT, pandas, yfinance, statsmodels, scipy, requests)
- [x] Config module (tickers, date range, paths)

## Phase 1 — Data acquisition
- [x] Ticker/sector universe: 5 large caps across 4 sectors (Financials: JPM, BAC; Technology: MSFT; Industrials: CAT; Energy: XOM) -- below the original 8-10 target; GOOGL/GS remain unverified candidates, JNJ/PG/WFC/AAPL evaluated and ruled out, see docs/data_sources.md
- [x] SEC EDGAR access built (CIK lookup, 8-K filing index) -- not the final transcript source (see below), but used for filing metadata
- [x] Curate transcript sources: 16 calls, each logged with exact source URL, publisher, retrieval date -> `docs/data_sources.md`
- [x] Pull daily OHLCV via yfinance for each ticker, event-window aligned
- [x] Pull Fama-French factor data (Kenneth French Data Library, daily) for the sample period

## Phase 2 — NLP pipeline
- [x] Segmentation: prepared-remarks blocks + per-question Q&A exchanges (src/nlp/segment.py)
- [x] FinBERT scoring per segment (ProsusAI/finbert)
- [x] Whole-transcript baseline score for comparison
- [x] Core-segment identification via keyword match (src/config.py UNIVERSE keywords)
- [x] Feature table: one row per call (data/processed/call_features.parquet)
- [x] Four transcript-format normalizers built as real formats were encountered (src/data/transcript_ingest.py): StreetEvents Q/A-tagged PDFs (JPM), inline-caps HTML (MSFT), bare-name-line PDFs needing roster lookup (BAC), caret-delimited PDFs with explicit roster (CAT)

## Phase 3 — Event study / statistics
- [x] Abnormal returns (Fama-French market-model adjusted) for [0,+1] and [0,+3] windows
- [x] Nested regression: dispersion's incremental R² over whole-transcript sentiment, with F-test
- [x] Small-N caveats reported inline with every regression result (not just once in a README)
- [x] Run at n=10 and n=16 -- see docs/results.md for the actual (null) result

## Phase 4 — Backtest (illustrative)
- [x] Long/short sort on dispersion signal
- [x] Transaction cost assumption (10bps/side, stated) and turnover reporting
- [x] Walk-forward split (min_train=10)
- [x] Probabilistic Sharpe Ratio (Bailey & Lopez de Prado 2012) instead of a raw-Sharpe text caveat -- see src/backtest/portfolio.py
- [x] Run at n=16 (first 6 out-of-sample trades) -- see docs/results.md for the actual (negative) result

## Phase 5 — Dashboard & writeup
- [x] Per-call view: segment sentiment heatmap vs. whole-transcript baseline (docs/figures/<TICKER>_<DATE>_segment_heatmap.png, one per call)
- [x] Portfolio-level view: dispersion-vs-return scatter, whole-vs-core sentiment comparison, backtest equity curve (docs/figures/)
- [x] Final report: docs/results.md states the hypothesis, method, and the current null result plainly, including the specific finding that R² shrank (not grew) from n=10 to n=16 -- evidence the early result was noise

## Status: core loop complete, sample still small
The full pipeline (data -> NLP -> statistics -> backtest -> figures) runs
end-to-end and has been exercised at two sample-size checkpoints (n=10,
n=16), both producing an honestly-reported null result. What's left is
scale, not new methodology:

- [ ] Grow the sample toward n=25-30 (original target) by adding more
      quarters for existing tickers and/or verifying a first-party source
      for GOOGL, GS, or a healthcare/consumer name to add sector diversity
- [ ] Re-run `src.run_pipeline` and update `docs/results.md` at each
      meaningful size increase

## Explicit non-goals
- Not claiming a deployable production alpha signal
- Not doing full-universe/long-history backtesting (small curated sample by design)
- Not using paid data (WRDS/CRSP/Compustat/Bloomberg)
