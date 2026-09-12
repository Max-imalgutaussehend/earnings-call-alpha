# Results (current sample)

Regenerate this by running `python3 -m src.run_pipeline` and reading its
output; this file is a narrated snapshot of that output plus interpretation,
not a substitute for re-running the pipeline yourself.

## Current sample: n=2 calls (JPM 4Q25, MSFT FY26 Q4)

This is far below the ~25-40 call target in `docs/plan.md`. At n=2, the
nested-regression test (H1) and the walk-forward backtest both correctly
report "sample too small" rather than a spurious p-value or Sharpe ratio —
see `src/backtest/event_study.py::nested_regression_test` and
`src/backtest/portfolio.py::summarize_backtest`. That is by design: a
statistics module that silently produces a number regardless of n is worse
than one that refuses.

## What the 2 calls do show (illustrative, not yet a tested hypothesis)

| Ticker | Call date | Whole-transcript sentiment | Core-segment sentiment | Dispersion |
|--------|-----------|------------------------------|--------------------------|------------|
| JPM | 2026-01-13 | +0.078 | +0.070 (consumer/community banking segments) | 1.00 |
| MSFT | 2026-07-29 | +0.009 (~neutral) | +0.248 (Azure/cloud segments) | 0.71 |

The MSFT result is the qualitative example the whole project is built
around: the whole-transcript score is almost exactly neutral, while the
segments discussing Azure/cloud — the company's stated largest growth
driver this quarter — score clearly positive. A sentiment measure that only
looked at the whole-transcript average would have missed that the call's
substantive content about the company's core business was strongly
positive; averaging in the rest of the call (competitive/regulatory
questions, cost commentary) pulled the aggregate back toward neutral. See
`docs/figures/whole_vs_core_sentiment.png`.

This is exactly the failure mode H1 predicts whole-transcript sentiment
should have. It is **one data point**, not evidence — the honest framing
is "the mechanism the hypothesis describes is visibly present here," not
"H1 is confirmed."

## Figures

- `docs/figures/JPM_2026-01-13_segment_heatmap.png` / `MSFT_2026-07-29_segment_heatmap.png` — every scored segment's sentiment vs. the whole-transcript baseline (dashed line). Segments crossing far from the baseline in either direction are the ones driving dispersion.
- `docs/figures/whole_vs_core_sentiment.png` — the headline comparison above.
- `docs/figures/dispersion_vs_return_1d.png` — currently just 2 points; not interpretable yet, kept in the repo so the figure updates automatically as more calls are added.

## What would change this from "illustrative" to "tested"

1. Reach n>=10 calls (regression test's own threshold) for the nested
   regression to run at all; n>=25-30 for the walk-forward backtest to have
   more than a handful of out-of-sample trades.
2. At that point, re-run `src.run_pipeline` and report the actual
   incremental-R² and PSR numbers here, including if H1 does NOT hold —
   see `docs/methodology.md`'s statistical honesty checklist.
