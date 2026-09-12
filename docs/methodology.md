# Methodology Notes

## Why FinBERT as the primary scorer (not a general LLM)

See `src/nlp/finbert.py` docstring for the full rationale (determinism, cost
at this scale, financial-domain fit). In short: the backtest's validity
depends on the sentiment score being a stable, reproducible function of the
text, and FinBERT gives that by construction where an LLM-as-judge does not
unless heavily constrained (fixed seed/temperature=0 still doesn't guarantee
bit-identical outputs across API versions).

## Segmentation approach

Rule-based (regex + speaker-role heuristics), not a learned segmenter — see
`src/nlp/segment.py`. Given the sample size (~25-40 calls), a transparent,
auditable rule-based splitter is preferable to a black-box one: every
segmentation decision can be inspected and corrected by hand if it's wrong,
which matters more than marginal accuracy gains from a learned approach at
this scale.

## Event-study design

Standard short-window market-model event study (Brown & Warner 1985-style):
beta estimated on a trailing 60-trading-day window, expected return computed
from the single-factor (Mkt-RF) model, abnormal return = realized − expected,
summed over the event window ([0,+1] and [0,+3] trading days). This is a
textbook approach chosen for transparency over a multi-factor model, given
the small sample doesn't support estimating many factor loadings reliably
per stock.

## Statistical honesty checklist (applied to every result reported)

- [ ] Sample size (n) stated alongside every effect size
- [ ] p-values reported without cherry-picking the best event window
- [ ] Nested-regression test used (not just "correlation exists") to isolate
      the *incremental* contribution of the dispersion signal
- [ ] Walk-forward split used for the backtest, not a single in-sample fit
- [ ] Backtest Sharpe explicitly flagged as unreliable at this sample size
      (small-N Sharpe ratios are dominated by luck; see Bailey & López de
      Prado's deflated Sharpe ratio literature for why)
- [ ] A null result (H1 not supported) is reported as a finding, not omitted

## Known threats to validity

- **Look-ahead bias in core-segment identification**: the keyword list for
  each ticker's "core segment" (`src/config.py`) is chosen using current
  knowledge of the company's business mix. For older calls, the company's
  actual largest segment may have differed. This is a real limitation and is
  disclosed rather than fixed with a bigger data pipeline that's out of scope
  for a portfolio project.
- **Small, non-random sample**: tickers and calls are curated for coverage
  and transcript availability, not randomly sampled — so results should not
  be read as generalizing to the broader market.
- **Transcript formatting inconsistency**: since transcripts come from
  multiple first-party sources (SEC exhibits, IR sites), speaker-label
  formatting varies. The segmenter is regex-based and may occasionally
  mis-attribute a turn; spot-checking segmentation output against the raw
  transcript is part of the Phase 2 QA step.
- **Multi-turn answers within one Q&A exchange**: when a question is
  answered by more than one executive in sequence (e.g. CFO answers, CEO
  adds a comment, CFO continues), the current segmenter (`src/nlp/segment.py`)
  pairs the question only with the *first* subsequent non-analyst turn and
  treats later turns in the same exchange as standalone answer-only segments
  (question text not repeated). This under-counts how much text is
  attributed to "the" answer for that question. Accepted as a known
  limitation given the small, hand-auditable sample rather than building a
  more elaborate multi-turn grouping heuristic — call it out explicitly
  rather than silently absorb it into the dispersion feature.
- **Sell-side firm name matching is a fixed, non-exhaustive list**
  (`SELL_SIDE_FIRM_WORDS` in `src/nlp/segment.py`) used as a fallback when a
  transcript labels analysts by firm rather than the word "Analyst". Works
  for the curated universe's observed sources (JPM, MSFT) but is not a
  general analyst-detector; extend the list before adding a new source.
