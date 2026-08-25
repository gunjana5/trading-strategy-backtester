# fetcher normalisation - mock yfinance, never hit the network

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from data import fetcher


def _idx(n=5):
    return pd.date_range("2024-01-01", periods=n, freq="B")


def test_fetch_uses_cache(monkeypatch, tmp_path):
    from data import cache as cache_mod

    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        raise AssertionError("should not download when cache hits")

    monkeypatch.setattr(fetcher.yf, "download", boom)
    frame = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.1] * 3,
            "low": [0.9] * 3,
            "close": [1.0, 1.1, 1.2],
            "volume": [100.0] * 3,
        },
        index=_idx(3),
    )
    cache_mod.set_cached_ohlcv("AAPL", "2024-01-01", "2024-02-01", frame)
    out = fetcher.fetch_ohlcv("aapl", "2024-01-01", "2024-02-01")
    assert len(out) == 3
    assert called["n"] == 0


def test_normalises_multiindex_columns(monkeypatch, tmp_path):
    from data import cache as cache_mod

    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    idx = _idx(4)
    cols = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"], ["AAPL"]])
    raw = pd.DataFrame(np.ones((4, 5)), index=idx, columns=cols)
    raw.iloc[:, 3] = [10, 11, 12, 13]

    monkeypatch.setattr(fetcher.yf, "download", MagicMock(return_value=raw))
    out = fetcher.fetch_ohlcv("aapl", "2024-01-01", "2024-02-01")
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]
    assert float(out["close"].iloc[-1]) == 13.0


def test_falls_back_to_adj_close(monkeypatch, tmp_path):
    from data import cache as cache_mod

    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    idx = _idx(3)
    raw = pd.DataFrame(
        {
            "Open": [1, 1, 1],
            "High": [1, 1, 1],
            "Low": [1, 1, 1],
            "Adj Close": [9.0, 9.5, 10.0],
            "Volume": [100, 100, 100],
        },
        index=idx,
    )
    monkeypatch.setattr(fetcher.yf, "download", MagicMock(return_value=raw))
    out = fetcher.fetch_ohlcv("msft", "2024-01-01", "2024-02-01")
    assert "close" in out.columns
    assert float(out["close"].iloc[0]) == 9.0


def test_empty_download_raises(monkeypatch, tmp_path):
    from data import cache as cache_mod

    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(fetcher.yf, "download", MagicMock(return_value=pd.DataFrame()))
    with pytest.raises(ValueError, match="no data"):
        fetcher.fetch_ohlcv("zzzz", "2024-01-01", "2024-02-01")


def test_missing_columns_raises(monkeypatch, tmp_path):
    from data import cache as cache_mod

    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    idx = _idx(2)
    raw = pd.DataFrame({"Close": [1.0, 2.0]}, index=idx)
    monkeypatch.setattr(fetcher.yf, "download", MagicMock(return_value=raw))
    with pytest.raises(ValueError, match="missing columns"):
        fetcher.fetch_ohlcv("aapl", "2024-01-01", "2024-02-01")


def test_demo_ticker_loads_fixture_without_yahoo(monkeypatch):
    # DEMO must never call yfinance
    monkeypatch.setattr(
        fetcher.yf,
        "download",
        MagicMock(side_effect=AssertionError("demo should not hit yahoo")),
    )
    out = fetcher.fetch_ohlcv("demo", "2023-01-01", "2024-12-31")
    assert len(out) > 100
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]
    sliced = fetcher.fetch_ohlcv("DEMO", "2023-06-01", "2023-06-30")
    assert len(sliced) < len(out)
    assert sliced.index.min() >= pd.Timestamp("2023-06-01")
