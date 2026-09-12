# Build Plan

## Phase 0 — Setup (this session)
- [x] Repo structure
- [ ] Python env (torch + transformers + FinBERT, pandas, yfinance, statsmodels, requests)
- [ ] Config module (tickers, date range, paths)

## Phase 1 — Data acquisition
- [ ] Ticker/sector universe: pick 8-10 large caps across >=4 sectors
- [ ] Pull SEC EDGAR submission history per ticker (CIK lookup, 8-K filings with Ex-99.1/99.2)
- [ ] Curate transcript sources: for each selected call, record exact source URL, publisher, retrieval date -> `docs/data_sources.md`
- [ ] Pull daily OHLCV via yfinance for each ticker, +/- 10 trading days around each call date
- [ ] Pull Fama-French factor data (Kenneth French Data Library, daily) for the sample period

## Phase 2 — NLP pipeline
- [ ] Segmentation: split each transcript into (a) prepared-remarks topic blocks, (b) per-question Q&A exchanges
- [ ] FinBERT scoring per segment (ProsusAI/finbert or yiyanghkust/finbert-tone) -> segment-level sentiment score + confidence
- [ ] Whole-transcript baseline score (same model, no segmentation) for comparison
- [ ] Identify "core segment" per call via keyword match to the firm's largest reported revenue segment (from 10-K segment reporting, EDGAR XBRL)
- [ ] Feature table: one row per call with whole-transcript sentiment, max/min/dispersion, core-segment sentiment

## Phase 3 — Event study / statistics
- [ ] Compute abnormal returns (Fama-French adjusted) for [0,+1] and [0,+3] windows
- [ ] Nested regression: does dispersion/core-segment sentiment add R^2 beyond whole-transcript sentiment?
- [ ] Report information coefficients with confidence intervals, and explicitly flag small-N / multiple-testing caveats (this is the rigor signal — don't skip it)

## Phase 4 — Backtest (illustrative)
- [ ] Long/short sort on dispersion signal
- [ ] Transaction cost assumption (stated, e.g. 10bps/side) and turnover reporting
- [ ] Walk-forward split (train sentiment-return relationship on first N calls, test on later ones) rather than a single in-sample fit
- [ ] Report Sharpe with explicit small-sample caveat (deflated Sharpe ratio note)

## Phase 5 — Dashboard & writeup
- [ ] Per-call view: transcript -> segment sentiment heatmap -> predicted vs realized reaction
- [ ] Portfolio-level view: signal distribution, backtest equity curve
- [ ] Final report: hypothesis, method, result, and — if it's a null result — say so as the finding

## Explicit non-goals
- Not claiming a deployable production alpha signal
- Not doing full-universe/long-history backtesting (small curated sample by design)
- Not using paid data (WRDS/CRSP/Compustat/Bloomberg)
