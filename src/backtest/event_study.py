"""Event study: abnormal returns around each call, and nested-regression test
of whether segment dispersion adds explanatory power beyond whole-transcript
sentiment.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.config import EVENT_WINDOWS
from src.data.prices import fetch_fama_french_daily, fetch_prices


def compute_abnormal_return(ticker: str, call_date: str, window_days: int) -> float | None:
    """Fama-French-adjusted abnormal return over [0, window_days] trading days
    after the call date. Uses the single-factor (Mkt-RF) model estimated on
    the trailing 60 trading days for expected return, consistent with
    standard event-study methodology (Brown & Warner, 1985 style short-window
    market-model approach).
    """
    d0 = datetime.strptime(call_date, "%Y-%m-%d").date()
    px = fetch_prices(ticker, d0 - timedelta(days=100), d0 + timedelta(days=window_days + 10))
    ff = fetch_fama_french_daily()

    px = px.copy()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    px["ret"] = px["Close"].pct_change()

    merged = px[["ret"]].join(ff, how="inner").dropna()
    if merged.empty:
        return None

    event_idx = merged.index.searchsorted(pd.Timestamp(d0))
    est_window = merged.iloc[max(0, event_idx - 60) : event_idx]
    if len(est_window) < 20:
        return None

    X = sm.add_constant(est_window["Mkt-RF"])
    y = est_window["ret"] - est_window["RF"]
    beta_model = sm.OLS(y, X).fit()

    event_window = merged.iloc[event_idx : event_idx + window_days + 1]
    if event_window.empty:
        return None

    expected = beta_model.params["const"] + beta_model.params["Mkt-RF"] * event_window["Mkt-RF"] + event_window["RF"]
    abnormal = event_window["ret"] - expected
    return float(abnormal.sum())


def build_event_study_table(calls: list[dict]) -> pd.DataFrame:
    """calls: list of dicts with ticker, call_date, whole_sentiment, dispersion, core_segment_sentiment"""
    rows = []
    for c in calls:
        row = dict(c)
        for w in EVENT_WINDOWS:
            row[f"abn_ret_{w}d"] = compute_abnormal_return(c["ticker"], c["call_date"], w)
        rows.append(row)
    return pd.DataFrame(rows)


def nested_regression_test(df: pd.DataFrame, target_col: str = "abn_ret_1d") -> dict:
    """Compare R^2 of (a) whole_sentiment only vs (b) whole_sentiment + dispersion.
    Reports the incremental R^2 and an F-test p-value for whether dispersion's
    coefficient is significantly different from zero -- the actual test of H1.
    """
    d = df.dropna(subset=["whole_sentiment", "dispersion", target_col])
    if len(d) < 10:
        return {"n": len(d), "note": "Sample too small for a meaningful regression test (n<10)."}

    y = d[target_col]
    X_base = sm.add_constant(d[["whole_sentiment"]])
    X_full = sm.add_constant(d[["whole_sentiment", "dispersion"]])

    m_base = sm.OLS(y, X_base).fit()
    m_full = sm.OLS(y, X_full).fit()

    f_test = m_full.compare_f_test(m_base)

    return {
        "n": len(d),
        "r2_base": m_base.rsquared,
        "r2_full": m_full.rsquared,
        "incremental_r2": m_full.rsquared - m_base.rsquared,
        "dispersion_coef": m_full.params.get("dispersion"),
        "dispersion_pvalue": m_full.pvalues.get("dispersion"),
        "f_test_pvalue": f_test[1],
        "caveat": (
            "Small-N study (n="
            f"{len(d)}). This p-value is a single test on a curated sample, not "
            "a multiple-testing-corrected result across the full universe. "
            "Treat as suggestive evidence, not a confirmed effect."
        ),
    }
