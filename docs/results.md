# Results (current sample)

Regenerate this by running `python3 -m src.run_pipeline` and reading its
output; this file is a narrated snapshot of that output plus interpretation,
not a substitute for re-running the pipeline yourself.

## Current sample: n=10 calls, 5 tickers, 4 sectors

| Ticker | Sector | Call dates covered |
|--------|--------|---------------------|
| JPM | Financials | 2026-01-13, 2026-07-14 |
| BAC | Financials | 2026-04-15, 2026-07-14 |
| MSFT | Technology | 2026-07-29 |
| CAT | Industrials | 2025-10-29, 2026-01-29, 2026-04-30 |
| XOM | Energy | 2024-08-02, 2026-01-30 |

Still below the ~25-40 call target in `docs/plan.md`, but n=10 is exactly
the nested-regression test's own minimum threshold, so **the regression now
actually runs** rather than reporting "sample too small." The walk-forward
backtest still reports no trades — it needs `min_train=10` calls just to
produce its *first* out-of-sample trade, so n>=15-20 is needed before it
generates anything.

## H1 test result (nested regression): NOT SUPPORTED at this sample size

```
target: abn_ret_1d   n=10   r2_base=0.176  r2_full=0.200  incremental_r2=0.025
                      dispersion_pvalue=0.657   f_test_pvalue=0.657
target: abn_ret_3d   n=10   r2_base=0.310  r2_full=0.355  incremental_r2=0.045
                      dispersion_pvalue=0.508   f_test_pvalue=0.508
```

Segment-sentiment dispersion adds a small amount of R² (2.5-4.5 percentage
points) over whole-transcript sentiment alone, but the added coefficient is
**not statistically distinguishable from zero** at this sample size
(p=0.51-0.66, far above conventional thresholds even before any
multiple-testing correction). This is reported as a finding, not hidden:
**H1 is not supported by the current 10-call sample.** This is an expected
and informative outcome at n=10, not a failure of the pipeline — see
`docs/methodology.md`'s statistical honesty checklist, which requires
reporting null results rather than only positive ones.

This result should be revisited once the sample reaches n=25-30: at n=10, a
true effect of the size hypothesized in Kim et al. 2025 (arXiv:2505.16090)
would very plausibly still fail to reach significance simply from lack of
power, so "not supported yet" is the accurate statement — not "H1 is false."

## What the individual calls show (illustrative, pre-existing observation)

| Ticker | Call date | Whole-transcript sentiment | Core-segment sentiment | Dispersion |
|--------|-----------|------------------------------|--------------------------|------------|
| JPM | 2026-01-13 | +0.078 | +0.070 | 1.00 |
| JPM | 2026-07-14 | +0.149 | +0.075 | 0.36 |
| MSFT | 2026-07-29 | +0.009 (~neutral) | +0.249 (Azure/cloud) | 0.71 |
| BAC | 2026-07-14 | +0.938 | +0.493 | 1.47 |
| BAC | 2026-04-15 | +0.911 | +0.266 | 1.02 |
| CAT | 2026-04-30 | +0.010 (~neutral) | +0.435 | 0.93 |
| CAT | 2026-01-29 | +0.006 (~neutral) | +0.440 | 1.81 |
| CAT | 2025-10-29 | +0.063 | +0.541 | 1.87 |
| XOM | 2024-08-02 | +0.911 | +0.308 | 0.89 |
| XOM | 2026-01-30 | +0.174 | +0.277 | 1.02 |

The MSFT and CAT calls are the clearest illustrations of the mechanism H1
describes: whole-transcript sentiment near zero while the company's
core/growth segment (Azure/cloud for MSFT; Construction & Resource
Industries commentary for CAT) scores clearly positive. See
`docs/figures/whole_vs_core_sentiment.png`. JPM and BAC show smaller,
same-direction gaps; XOM's 2024 call shows whole-transcript sentiment
already high with a *smaller* core-segment score, i.e. the opposite
direction — which is itself useful: it shows dispersion isn't a one-way
"whole-transcript underestimates the core story" effect, consistent with
the regression's finding that dispersion alone isn't a reliable predictor
yet at this n.

## Figures

- `docs/figures/<TICKER>_<DATE>_segment_heatmap.png` (10 files) — every scored segment's sentiment vs. the whole-transcript baseline (dashed line) for each call.
- `docs/figures/whole_vs_core_sentiment.png` — the headline whole-vs-core comparison across all 10 calls.
- `docs/figures/dispersion_vs_return_1d.png` — dispersion vs. abnormal return scatter across all 10 calls; visibly noisy, consistent with the regression's non-significant result.

## What would change this further

1. Reach n>=15-20 calls so the walk-forward backtest produces its first
   out-of-sample trades (currently `min_train=10` in
   `src/backtest/portfolio.py::walk_forward_signal_returns` consumes the
   entire current sample just as a training window).
2. Reach n>=25-30 for the regression test to have real power to detect an
   effect of realistic size, and to make the walk-forward backtest's PSR
   meaningful rather than based on a handful of trades.
3. At each size milestone, re-run `src.run_pipeline` and update this file
   with the actual numbers — including if H1 continues to not hold.
