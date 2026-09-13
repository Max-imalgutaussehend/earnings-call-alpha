"""Render the static results dashboard from the pipeline's own output.

Deliberately separate from the NLP/backtest pipeline: this module has no
torch/transformers dependency. It reads data/processed/call_features.parquet
(already scored by src.run_pipeline) plus a small results-summary JSON, and
renders one self-contained HTML file with inline SVG charts -- no client-side
JS charting library, no server-side model inference. That split is what
makes the *site* deployable on a small VM/container: the heavyweight FinBERT
scoring step runs once, locally or in CI, and only its output ever needs to
reach the server.

Usage:
    python3 -m src.site.render
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.backtest.event_study import nested_regression_test
from src.backtest.portfolio import summarize_backtest, walk_forward_signal_returns
from src.config import DATA_PROCESSED, ROOT, UNIVERSE

SITE_DIR = ROOT / "site"
TEMPLATES_DIR = SITE_DIR / "templates"
OUTPUT_DIR = SITE_DIR / "dist"
RESULTS_CACHE = DATA_PROCESSED / "results_summary.json"


def _sentiment_bar(value: float, scale: float = 150.0) -> dict:
    """Geometry for one diverging-bar-chart row, centered at x=0."""
    width = abs(value) * scale
    x = 0 if value >= 0 else -width
    return {"x": round(x, 2), "width": round(width, 2)}


def build_context() -> dict:
    df = pd.read_parquet(DATA_PROCESSED / "call_features.parquet").sort_values(["ticker", "call_date"])

    reg_1d = nested_regression_test(df, target_col="abn_ret_1d")
    reg_3d = nested_regression_test(df, target_col="abn_ret_3d")
    wf = walk_forward_signal_returns(df)
    backtest = summarize_backtest(wf)

    sector_by_ticker = {t: v["sector"] for t, v in UNIVERSE.items()}
    tickers = sorted(df["ticker"].unique())
    sample_rows = [
        {
            "ticker": t,
            "sector": sector_by_ticker.get(t, "—"),
            "dates": ", ".join(sorted(df[df["ticker"] == t]["call_date"].astype(str))),
            "n": int((df["ticker"] == t).sum()),
        }
        for t in tickers
    ]

    calls = []
    for _, row in df.iterrows():
        whole = float(row["whole_sentiment"])
        core = row.get("core_segment_sentiment")
        core = float(core) if pd.notna(core) else None
        disp = row.get("dispersion")
        disp = float(disp) if pd.notna(disp) else None
        calls.append(
            {
                "ticker": row["ticker"],
                "date": str(row["call_date"]),
                "whole": whole,
                "core": core,
                "dispersion": disp,
                "gap": (core - whole) if core is not None else None,
                "whole_bar": _sentiment_bar(whole),
                "core_bar": _sentiment_bar(core) if core is not None else None,
                "heatmap_img": f"figures/{row['ticker']}_{row['call_date']}_segment_heatmap.png",
            }
        )

    # cumulative walk-forward equity curve, for the backtest line chart
    equity_points = []
    if not wf.empty:
        wf_sorted = wf.sort_values("call_date").reset_index(drop=True)
        cum = (1 + wf_sorted["net_return"]).cumprod() - 1
        equity_points = [{"i": i, "cum_pct": round(float(v) * 100, 2)} for i, v in enumerate(cum)]

    def fmt_pct(x, digits=1):
        return None if x is None or pd.isna(x) else f"{x * 100:.{digits}f}%"

    def fmt_num(x, digits=3):
        return None if x is None or pd.isna(x) else f"{x:.{digits}f}"

    context = {
        "n_calls": len(df),
        "n_tickers": len(tickers),
        "n_sectors": len(set(sector_by_ticker.get(t, "") for t in tickers)),
        "tickers_list": ", ".join(tickers),
        "sample_rows": sample_rows,
        "calls": calls,
        "regression": {
            "1d": reg_1d,
            "3d": reg_3d,
        },
        "regression_fmt": {
            "1d": {
                "n": reg_1d.get("n"),
                "r2_base": fmt_num(reg_1d.get("r2_base")),
                "r2_full": fmt_num(reg_1d.get("r2_full")),
                "incremental_r2": fmt_pct(reg_1d.get("incremental_r2"), 1),
                "pvalue": fmt_num(reg_1d.get("dispersion_pvalue")),
            },
            "3d": {
                "n": reg_3d.get("n"),
                "r2_base": fmt_num(reg_3d.get("r2_base")),
                "r2_full": fmt_num(reg_3d.get("r2_full")),
                "incremental_r2": fmt_pct(reg_3d.get("incremental_r2"), 1),
                "pvalue": fmt_num(reg_3d.get("dispersion_pvalue")),
            },
        },
        "backtest": backtest,
        "backtest_fmt": {
            "n_trades": backtest.get("n_trades"),
            "cumulative_return": fmt_pct(backtest.get("cumulative_return"), 1),
            "sharpe_raw": fmt_num(backtest.get("sharpe_per_trade_raw"), 2),
            "psr": fmt_pct(backtest.get("probabilistic_sharpe_ratio"), 1),
        },
        "equity_points": equity_points,
        "has_regression": "note" not in reg_1d,
        "has_backtest": "note" not in backtest,
    }

    RESULTS_CACHE.write_text(json.dumps(context, indent=2, default=str))
    return context


def render():
    context = build_context()

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("dashboard.html.j2")
    html = template.render(**context)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "index.html"
    out_path.write_text(html)
    print(f"Rendered {out_path} ({len(html):,} bytes) from {context['n_calls']} calls.")
    return out_path


if __name__ == "__main__":
    render()
