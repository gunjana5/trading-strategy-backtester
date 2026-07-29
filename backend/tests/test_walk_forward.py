# synthetic ohlcv so ml tests stay offline

import numpy as np
import pandas as pd

from backtester.walk_forward import run_single_split, run_walk_forward


def _ohlcv(n=200, seed=0):
    # random walk close - just enough bars for features + folds
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0, 1, size=n))
    close = np.maximum(close, 5)
    volume = rng.integers(1_000_000, 5_000_000, size=n)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


def test_single_split_zeros_train_signals():
    df, meta = run_single_split(_ohlcv())
    assert meta["mode"] == "single_split"
    assert meta["train_rows"] > 0
    assert meta["test_rows"] > 0
    assert "signal" in df.columns
    # Early rows after features exist should be mostly 0 on train portion
    assert (df["signal"].fillna(0) == 0).sum() > 0


def test_walk_forward_produces_folds():
    # longer series so 3 expanding folds actually fit
    df, meta = run_walk_forward(_ohlcv(260), n_folds=3, min_train_rows=80)
    assert meta["mode"] == "walk_forward"
    assert meta["n_folds"] >= 2
    assert len(meta["folds"]) >= 2
    assert "mean_oos_accuracy" in meta
    # at least one oos bar should have a non-zero signal
    assert (df["signal"].abs() > 0).any()
