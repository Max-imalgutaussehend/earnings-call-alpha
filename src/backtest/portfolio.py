"""Illustrative long/short backtest on the dispersion signal.

Explicitly illustrative given small N (see README limitations) -- this is
not a claim of a deployable strategy. The point is to show the full
methodology (walk-forward split, transaction costs, turnover) rather than
to report an impressive Sharpe ratio from an overfit small sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

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


def probabilistic_sharpe_ratio(returns: pd.Series, benchmark_sr: float = 0.0) -> float | None:
    """P(true Sharpe > benchmark_sr) given the OBSERVED Sharpe, sample size,
    and the return distribution's skew/kurtosis (Bailey & Lopez de Prado,
    2012, "The Sharpe Ratio Efficient Frontier"). Unlike a plain Sharpe
    ratio, this explicitly penalizes small samples and non-normal returns
    instead of just noting "small N" as a caveat -- it turns the caveat into
    a number, which is the actual point of using it here.

    PSR = Phi( (SR_hat - SR_benchmark) * sqrt(n-1) /
               sqrt(1 - skew*SR_hat + (kurtosis-1)/4 * SR_hat^2) )
    """
    n = len(returns)
    if n < 3:
        return None
    sr_hat = returns.mean() / returns.std(ddof=1) if returns.std(ddof=1) > 0 else 0.0
    g3 = skew(returns, bias=False)
    g4 = kurtosis(returns, bias=False, fisher=False)  # non-excess (normal=3)

    denom = 1 - g3 * sr_hat + (g4 - 1) / 4 * sr_hat**2
    if denom <= 0:
        return None
    z = (sr_hat - benchmark_sr) * np.sqrt(n - 1) / np.sqrt(denom)
    return float(norm.cdf(z))


def summarize_backtest(returns_df: pd.DataFrame) -> dict:
    if returns_df.empty:
        return {"note": "No trades generated (insufficient walk-forward sample)."}

    net = returns_df["net_return"]
    n = len(net)
    mean_ret = net.mean()
    std_ret = net.std(ddof=1) if n > 1 else np.nan
    sharpe_per_trade = mean_ret / std_ret if std_ret and std_ret > 0 else np.nan
    psr = probabilistic_sharpe_ratio(net)

    return {
        "n_trades": n,
        "mean_net_return": mean_ret,
        "std_net_return": std_ret,
        "sharpe_per_trade_raw": sharpe_per_trade,
        "probabilistic_sharpe_ratio": psr,
        "cumulative_return": float((1 + net).prod() - 1),
        "caveat": (
            f"n={n} trades from a small curated sample. The probabilistic Sharpe "
            "ratio (PSR, Bailey & Lopez de Prado 2012) above already accounts for "
            "small-sample uncertainty and return skew/kurtosis when judging "
            "whether the raw Sharpe ratio is distinguishable from zero -- read "
            "that instead of the raw Sharpe ratio at this sample size. Both "
            "numbers should be read as illustrative of methodology, not as a "
            "performance claim."
        ),
    }
