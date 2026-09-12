"""Illustrative long/short backtest on the dispersion signal.

Explicitly illustrative given small N (see README limitations) -- this is
not a claim of a deployable strategy. The point is to show the full
methodology (walk-forward split, transaction costs, turnover) rather than
to report an impressive Sharpe ratio from an overfit small sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import TRANSACTION_COST_BPS


def walk_forward_signal_returns(
    df: pd.DataFrame, signal_col: str = "dispersion", return_col: str = "abn_ret_1d", min_train: int = 10
) -> pd.DataFrame:
    """Walk-forward: at each call (ordered by date), rank by signal using only
    prior calls' realized signal-return relationship (here: sign of the
    trailing correlation) to decide the long/short direction, rather than
    fitting on the full sample and testing in-sample.
    """
    d = df.dropna(subset=[signal_col, return_col]).sort_values("call_date").reset_index(drop=True)
    results = []
    for i in range(min_train, len(d)):
        train = d.iloc[:i]
        test_row = d.iloc[i]

        corr = train[signal_col].corr(train[return_col])
        direction = 1 if corr >= 0 else -1

        median_signal = train[signal_col].median()
        position = direction if test_row[signal_col] >= median_signal else -direction

        gross_return = position * test_row[return_col]
        cost = TRANSACTION_COST_BPS / 1e4  # one round-trip charged per trade
        net_return = gross_return - cost

        results.append(
            {
                "call_date": test_row["call_date"],
                "ticker": test_row["ticker"],
                "position": position,
                "gross_return": gross_return,
                "net_return": net_return,
            }
        )
    return pd.DataFrame(results)


def summarize_backtest(returns_df: pd.DataFrame) -> dict:
    if returns_df.empty:
        return {"note": "No trades generated (insufficient walk-forward sample)."}

    net = returns_df["net_return"]
    n = len(net)
    mean_ret = net.mean()
    std_ret = net.std(ddof=1) if n > 1 else np.nan
    sharpe_per_trade = mean_ret / std_ret if std_ret and std_ret > 0 else np.nan

    # Deflated Sharpe caveat: with small N, an apparently high Sharpe is
    # heavily inflated by luck. Flag rather than annualize/report uncritically.
    return {
        "n_trades": n,
        "mean_net_return": mean_ret,
        "std_net_return": std_ret,
        "sharpe_per_trade_raw": sharpe_per_trade,
        "cumulative_return": float((1 + net).prod() - 1),
        "caveat": (
            f"n={n} trades from a small curated sample. Sharpe ratios computed on "
            "such small samples are not reliable estimates of a deployable "
            "strategy's risk-adjusted return and should be read as illustrative "
            "of methodology, not as a performance claim."
        ),
    }
