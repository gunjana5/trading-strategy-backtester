# lock ma cross-day + rsi level semantics offline

import pandas as pd
import pytest

from strategies.moving_average import run as ma_run
from strategies.moving_average import sensitivity_grid
from strategies.rsi_strategy import run as rsi_run


def test_ma_signal_only_on_cross_day():
    # fast=2 slow=3 - craft a clear cross up then cross down
    # prices: flat low, then jump so fast crosses above slow, hold above, then dump
    closes = [
        10,
        10,
        10,  # warm-up
        10,
        10,
        20,
        20,
        20,  # after jump, fast should cross above
        20,
        20,
        5,
        5,
        5,  # dump - fast crosses below
    ]
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    df = pd.DataFrame({"close": closes}, index=idx)
    out = ma_run(df, fast=2, slow=3)
    sig = out["signal"].tolist()

    buy_days = [i for i, s in enumerate(sig) if s == 1]
    sell_days = [i for i, s in enumerate(sig) if s == -1]
    assert len(buy_days) >= 1
    assert len(sell_days) >= 1
    # stays 0 while price remains above / below - only fires on the cross
    assert buy_days[0] < sell_days[0]
    # no signal on the first bar
    assert sig[0] == 0
    # bars that are not cross events stay 0
    for i, s in enumerate(sig):
        if i not in buy_days and i not in sell_days:
            assert s == 0


def test_ma_no_signal_while_staying_above():
    # once crossed up, a gentle climb should not keep printing 1
    closes = [10, 10, 10, 10, 30, 31, 32, 33, 34]
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    df = pd.DataFrame({"close": closes}, index=idx)
    out = ma_run(df, fast=2, slow=3)
    assert (out["signal"] == 1).sum() == 1
    assert (out["signal"] == -1).sum() == 0


def test_rsi_levels_via_patched_indicator(monkeypatch):
    # patch ta to lock level rules without fighting rsi math
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame({"close": [100.0, 101, 102, 103, 104]}, index=idx)
    fake_rsi = pd.Series([float("nan"), 20.0, 50.0, 80.0, 40.0], index=idx)

    class FakeRSI:
        def __init__(self, _close, window=14):
            pass

        def rsi(self):
            return fake_rsi

    monkeypatch.setattr("strategies.rsi_strategy.ta.momentum.RSIIndicator", FakeRSI)
    out = rsi_run(df, period=14, overbought=70, oversold=30)
    assert out["signal"].tolist() == [0, 1, 0, -1, 0]


def test_sensitivity_grid_counts_pairs():
    closes = [10, 10, 10, 10, 30, 31, 32, 5, 5, 5, 5]
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    df = pd.DataFrame({"close": closes}, index=idx)
    rows = sensitivity_grid(df, [(2, 3), (2, 4)])
    assert len(rows) == 2
    assert rows[0]["fast"] == 2 and rows[0]["slow"] == 3
    assert "buy_signals" in rows[0] and "sell_signals" in rows[0]


def test_sensitivity_grid_rejects_bad_pair():
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=idx)
    with pytest.raises(ValueError, match="fast period must be smaller"):
        sensitivity_grid(df, [(5, 5)])
