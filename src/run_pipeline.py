"""Orchestrate the full pipeline for a list of curated calls.

Reads calls from data/raw/calls_manifest.csv (ticker, call_date, transcript_path),
computes NLP features, runs the event study, and writes the feature+return
table to data/processed/call_features.parquet, plus prints the regression
and backtest summary.

This is the single entrypoint that ties together src/nlp, src/data, and
src/backtest once transcripts have been collected (see docs/data_sources.md).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.backtest.event_study import build_event_study_table, nested_regression_test
from src.backtest.portfolio import summarize_backtest, walk_forward_signal_returns
from src.config import DATA_PROCESSED, DATA_RAW, UNIVERSE
from src.nlp.features import compute_call_features

MANIFEST_PATH = DATA_RAW / "calls_manifest.csv"


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"No manifest at {MANIFEST_PATH}. Create it with columns: "
            "ticker,call_date,transcript_path (see docs/data_sources.md)."
        )
    with open(MANIFEST_PATH, newline="") as f:
        return list(csv.DictReader(f))


def run():
    manifest = load_manifest()
    calls = []
    for row in manifest:
        ticker = row["ticker"]
        transcript_path = Path(row["transcript_path"])
        raw_text = transcript_path.read_text()
        core_keywords = UNIVERSE.get(ticker, {}).get("core_segment_keywords", [])

        feats = compute_call_features(ticker, row["call_date"], raw_text, core_keywords)
        calls.append(
            {
                "ticker": feats.ticker,
                "call_date": feats.call_date,
                "whole_sentiment": feats.whole_sentiment,
                "dispersion": feats.dispersion,
                "core_segment_sentiment": feats.core_segment_sentiment,
                "n_segments": feats.n_segments,
            }
        )
        print(f"Scored {ticker} {row['call_date']}: whole={feats.whole_sentiment:.3f} "
              f"dispersion={feats.dispersion:.3f} core={feats.core_segment_sentiment}")

    df = build_event_study_table(calls)
    df.to_parquet(DATA_PROCESSED / "call_features.parquet")
    print(f"\nSaved {len(df)} rows to {DATA_PROCESSED / 'call_features.parquet'}")

    print("\n=== Nested regression test (H1) ===")
    for window in ("abn_ret_1d", "abn_ret_3d"):
        print(f"\n-- target: {window} --")
        print(nested_regression_test(df, target_col=window))

    print("\n=== Illustrative walk-forward backtest ===")
    wf = walk_forward_signal_returns(df)
    print(summarize_backtest(wf))


if __name__ == "__main__":
    run()
