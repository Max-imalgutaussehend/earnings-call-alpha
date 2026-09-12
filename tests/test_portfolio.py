import numpy as np
import pandas as pd

from src.backtest.portfolio import probabilistic_sharpe_ratio, summarize_backtest


def test_psr_none_for_tiny_sample():
    assert probabilistic_sharpe_ratio(pd.Series([0.01, 0.02])) is None


def test_psr_low_for_noisy_near_zero_returns():
    rng = np.random.default_rng(0)
    rets = pd.Series(rng.normal(0.0, 0.02, 20))
    psr = probabilistic_sharpe_ratio(rets)
    assert psr is not None
    assert 0.0 <= psr <= 1.0


def test_psr_high_for_strong_consistent_positive_returns():
    rets = pd.Series([0.01] * 30)  # deterministic positive, zero variance -> skip
    rets = rets + np.linspace(-0.0001, 0.0001, 30)  # tiny noise to keep std > 0
    psr = probabilistic_sharpe_ratio(rets)
    assert psr is not None
    assert psr > 0.99


def test_summarize_backtest_includes_psr_and_caveat():
    rets = pd.DataFrame({"net_return": [0.001, -0.002, 0.003, 0.0005, -0.001] * 3})
    summary = summarize_backtest(rets)
    assert "probabilistic_sharpe_ratio" in summary
    assert "caveat" in summary
    assert summary["n_trades"] == 15


def test_summarize_backtest_empty_returns_note():
    assert "note" in summarize_backtest(pd.DataFrame())
