"""Plots for the per-call segment-sentiment story and the aggregate results.

Kept as plain matplotlib (no seaborn/plotly dependency) so the project has
one less thing to install to reproduce a figure.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FIGURES_DIR = Path(__file__).resolve().parents[2] / "docs" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

_POS_COLOR = "#1a7a4c"
_NEG_COLOR = "#b33f3f"
_NEU_COLOR = "#8a8a8a"


def _sentiment_color(v: float) -> str:
    if v > 0.15:
        return _POS_COLOR
    if v < -0.15:
        return _NEG_COLOR
    return _NEU_COLOR


def plot_call_segment_heatmap(ticker: str, call_date: str, segment_labels: list[str], segment_scores: list[float], whole_sentiment: float, out_name: str | None = None):
    """Per-call view: each segment's sentiment as a horizontal bar, with the
    whole-transcript baseline marked as a vertical reference line -- this is
    the chart that makes the core H1 story visible at a glance: segments
    diverging strongly from the baseline line is the dispersion signal.
    """
    n = len(segment_scores)
    fig, ax = plt.subplots(figsize=(10, max(2.5, 0.35 * n)))

    y_pos = np.arange(n)
    colors = [_sentiment_color(s) for s in segment_scores]
    ax.barh(y_pos, segment_scores, color=colors, height=0.65)
    ax.axvline(whole_sentiment, color="black", linestyle="--", linewidth=1.2, label=f"Whole-transcript sentiment ({whole_sentiment:+.2f})")
    ax.axvline(0, color="#cccccc", linewidth=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(segment_labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(-1.05, 1.05)
    ax.set_xlabel("FinBERT sentiment (P(positive) - P(negative))")
    ax.set_title(f"{ticker} {call_date}: segment-level sentiment vs. whole-transcript baseline")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()

    out_name = out_name or f"{ticker}_{call_date}_segment_heatmap.png"
    path = FIGURES_DIR / out_name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_dispersion_vs_return(df: pd.DataFrame, return_col: str = "abn_ret_1d", out_name: str = "dispersion_vs_return.png"):
    """Scatter: segment dispersion (x) vs. abnormal return (y), one point per
    call, labeled by ticker. This is the plot a reviewer will look at first
    to sanity-check whether H1 has any visible signal before reading the
    regression table.
    """
    d = df.dropna(subset=["dispersion", return_col])
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(d["dispersion"], d[return_col], s=60, color="#2b6cb0", zorder=3)
    for _, row in d.iterrows():
        ax.annotate(f"{row['ticker']} {row['call_date']}", (row["dispersion"], row[return_col]), fontsize=7, xytext=(5, 5), textcoords="offset points")

    if len(d) >= 2:
        z = np.polyfit(d["dispersion"], d[return_col], 1)
        xs = np.linspace(d["dispersion"].min(), d["dispersion"].max(), 50)
        ax.plot(xs, np.polyval(z, xs), color="#999999", linestyle="--", linewidth=1, zorder=2, label="OLS fit (illustrative, n too small for inference)")
        ax.legend(fontsize=8)

    ax.axhline(0, color="#cccccc", linewidth=0.8)
    ax.set_xlabel("Segment sentiment dispersion (max - min)")
    ax.set_ylabel(f"Abnormal return ({return_col})")
    ax.set_title("Segment dispersion vs. abnormal return, per call")
    fig.tight_layout()

    path = FIGURES_DIR / out_name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_whole_vs_core_sentiment(df: pd.DataFrame, out_name: str = "whole_vs_core_sentiment.png"):
    """Bar chart contrasting whole-transcript sentiment with core-segment
    sentiment per call -- the chart that directly illustrates the motivating
    example (a company's overall tone masking strength/weakness in its
    largest business line).
    """
    d = df.dropna(subset=["whole_sentiment", "core_segment_sentiment"]).copy()
    d["label"] = d["ticker"] + " " + d["call_date"].astype(str)

    x = np.arange(len(d))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(x - width / 2, d["whole_sentiment"], width, label="Whole-transcript sentiment", color="#4a5568")
    ax.bar(x + width / 2, d["core_segment_sentiment"], width, label="Core-segment sentiment", color="#2b6cb0")
    ax.axhline(0, color="#cccccc", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(d["label"], fontsize=8)
    ax.set_ylabel("FinBERT sentiment")
    ax.set_title("Whole-transcript vs. core-segment sentiment")
    ax.legend(fontsize=8)
    fig.tight_layout()

    path = FIGURES_DIR / out_name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_backtest_equity_curve(returns_df: pd.DataFrame, out_name: str = "backtest_equity_curve.png"):
    if returns_df.empty:
        return None
    d = returns_df.sort_values("call_date").copy()
    d["cum_net"] = (1 + d["net_return"]).cumprod() - 1

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(range(len(d)), d["cum_net"] * 100, marker="o", color="#2b6cb0")
    ax.axhline(0, color="#cccccc", linewidth=0.8)
    ax.set_xlabel("Trade sequence (walk-forward order)")
    ax.set_ylabel("Cumulative net return (%)")
    ax.set_title(f"Illustrative walk-forward backtest equity curve (n={len(d)} trades)")
    fig.tight_layout()

    path = FIGURES_DIR / out_name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
