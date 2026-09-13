# Results (current sample)

Regenerate this by running `python3 -m src.run_pipeline` and reading its
output; this file is a narrated snapshot of that output plus interpretation,
not a substitute for re-running the pipeline yourself.

## Current sample: n=16 calls, 5 tickers, 4 sectors

| Ticker | Sector | Call dates covered |
|--------|--------|---------------------|
| JPM | Financials | 2025-07-15, 2025-10-14, 2026-01-13, 2026-04-14, 2026-07-14 |
| BAC | Financials | 2026-04-15, 2026-07-14 |
| MSFT | Technology | 2026-07-29 |
| CAT | Industrials | 2025-08-05, 2025-10-29, 2026-01-29, 2026-04-30 |
| XOM | Energy | 2024-08-02, 2025-01-31, 2026-01-30, 2026-05-01 |

Still below the ~25-40 call target in `docs/plan.md`, but past two
meaningful thresholds: n>=10 (the regression test's own minimum) and
n>=10+`min_train` (the walk-forward backtest's minimum to produce even one
out-of-sample trade). At n=16 the backtest now produces 6 trades.

## H1 test result (nested regression): NOT SUPPORTED, and getting weaker

```
target: abn_ret_1d   n=16   r2_base=0.055  r2_full=0.062  incremental_r2=0.008
                      dispersion_pvalue=0.748   f_test_pvalue=0.748
target: abn_ret_3d   n=16   r2_base=0.054  r2_full=0.061  incremental_r2=0.006
                      dispersion_pvalue=0.776   f_test_pvalue=0.776
```

Compare to the n=10 result (incremental R² 2.5-4.5pp, p=0.51-0.66): with 6
more calls added, the incremental R² from dispersion actually **shrank**
(to 0.6-0.8pp) and the p-values got **less** significant (0.75-0.78). This
is the expected behavior of noise, not signal — a real effect should get
more (not less) distinguishable from zero as n grows. This is meaningful
evidence, at this sample size, that dispersion's apparent contribution at
n=10 was likely noise rather than an emerging real effect.

## Backtest result: negative, low-confidence

```
n_trades=6   mean_net_return=-3.50%   cumulative_return=-20.2%
sharpe_per_trade_raw=-0.524   probabilistic_sharpe_ratio=0.063
```

The illustrative long/short backtest lost money over its first 6
out-of-sample trades, and the Probabilistic Sharpe Ratio (6.3%) says there
is essentially no basis to believe the true Sharpe ratio is positive — the
opposite conclusion from what a deployable-strategy claim would need. This
is consistent with the regression result: **at n=16, neither test supports
H1.**

## Honest interim conclusion

Two independent tests (nested regression, walk-forward backtest) now both
point the same direction: dispersion in segment-level sentiment, as
currently measured, does not show a reliable relationship with short-horizon
abnormal returns in this sample. The regression's *R² shrinking* as n grew
from 10 to 16 is a specific, checkable warning sign of an n=10 result being
noise — worth stating plainly rather than only citing the more flattering
early number.

This is not being treated as a final verdict — n=16 is still small, and the
same argument (small-sample instability) that flags the n=10 result as
possibly spurious also means the n=16 result isn't yet a confident null
either. The honest position is: **no evidence of the effect so far,
strength of that "no evidence" still limited by sample size.** See
`docs/methodology.md`'s statistical honesty checklist for why both this
file and the pipeline itself are built to report exactly this kind of
result rather than only chase a positive-looking one.

## What the individual calls show (illustrative, mechanism-level observation)

| Ticker | Call date | Whole-transcript sentiment | Core-segment sentiment | Dispersion |
|--------|-----------|------------------------------|--------------------------|------------|
| JPM | 2025-07-15 | +0.061 | -0.122 | 1.20 |
| JPM | 2025-10-14 | -0.098 | -0.049 | 0.71 |
| JPM | 2026-01-13 | +0.078 | +0.070 | 1.00 |
| JPM | 2026-04-14 | +0.076 | +0.052 | 1.11 |
| JPM | 2026-07-14 | +0.149 | +0.075 | 0.36 |
| BAC | 2026-04-15 | +0.911 | +0.266 | 1.02 |
| BAC | 2026-07-14 | +0.938 | +0.493 | 1.47 |
| MSFT | 2026-07-29 | +0.009 (~neutral) | +0.249 (Azure/cloud) | 0.71 |
| CAT | 2025-08-05 | +0.045 | -0.032 | 1.74 |
| CAT | 2025-10-29 | +0.063 | +0.541 | 1.87 |
| CAT | 2026-01-29 | +0.006 (~neutral) | +0.440 | 1.81 |
| CAT | 2026-04-30 | +0.010 (~neutral) | +0.435 | 0.93 |
| XOM | 2024-08-02 | +0.911 | +0.308 | 0.89 |
| XOM | 2025-01-31 | +0.716 | +0.328 | 0.92 |
| XOM | 2026-01-30 | +0.174 | +0.277 | 1.02 |
| XOM | 2026-05-01 | +0.643 | +0.451 | 0.96 |

With more calls per ticker now visible, the mechanism the project set out
to illustrate (whole-transcript sentiment masking a distinct core-segment
signal) shows up inconsistently: MSFT and most CAT calls show a clear gap in
the hypothesized direction, while two JPM calls and one CAT call show the
core segment scoring *more negative* than the whole transcript — the
opposite direction. This within-ticker inconsistency across quarters is
itself informative: it's a plausible reason the pooled-sample regression
finds no reliable relationship. See `docs/figures/whole_vs_core_sentiment.png`.

## Figures

- `docs/figures/<TICKER>_<DATE>_segment_heatmap.png` (16 files) — every scored segment's sentiment vs. the whole-transcript baseline (dashed line) for each call.
- `docs/figures/whole_vs_core_sentiment.png` — the whole-vs-core comparison across all 16 calls.
- `docs/figures/dispersion_vs_return_1d.png` — dispersion vs. abnormal return scatter; visibly noisy, consistent with both tests' non-significant results.
- `docs/figures/backtest_equity_curve.png` — the 6-trade walk-forward equity curve, trending down.

## What would change this further

1. Reach n>=25-30 (the original target) to have a sample large enough that
   a genuinely small real effect wouldn't be swamped by the shrinking-R²
   pattern seen going from n=10 to n=16.
2. Add tickers from sectors not yet represented (Healthcare, Consumer) once
   a first-party transcript source is found for one — JNJ and PG were both
   evaluated and ruled out (see `docs/data_sources.md`); a different
   healthcare/consumer name would need the same verification before adding.
3. At each size milestone, re-run `src.run_pipeline` and update this file
   with the actual numbers — including if H1 continues to not hold. A
   stable null across n=10, n=16, and n=25+ would itself be a complete,
   reportable, defensible finding for this project.
