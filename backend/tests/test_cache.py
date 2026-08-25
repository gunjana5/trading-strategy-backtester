# cache ttl - temp sqlite, no yahoo

from datetime import datetime, timedelta, timezone

import pandas as pd

from data import cache as cache_mod


def _frame():
    idx = pd.date_range("2024-01-01", periods=3, freq="B")
    return pd.DataFrame(
        {
            "open": [1.0, 1.0, 1.0],
            "high": [1.1, 1.1, 1.1],
            "low": [0.9, 0.9, 0.9],
            "close": [1.0, 1.05, 1.1],
            "volume": [10.0, 10.0, 10.0],
        },
        index=idx,
    )


def test_cache_hit_within_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    cache_mod.set_cached_ohlcv("AAPL", "2024-01-01", "2024-02-01", _frame())
    hit = cache_mod.get_cached_ohlcv("aapl", "2024-01-01", "2024-02-01")
    assert hit is not None
    assert len(hit) == 3


def test_cache_miss_after_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(cache_mod, "_TTL", timedelta(hours=24))
    cache_mod.set_cached_ohlcv("MSFT", "2024-01-01", "2024-02-01", _frame())

    # rewrite fetched_at to yesterday
    key = cache_mod._cache_key("MSFT", "2024-01-01", "2024-02-01")
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    with cache_mod._connect() as conn:
        conn.execute(
            "UPDATE ohlcv_cache SET fetched_at = ? WHERE cache_key = ?",
            (stale, key),
        )
        conn.commit()

    miss = cache_mod.get_cached_ohlcv("MSFT", "2024-01-01", "2024-02-01")
    assert miss is None


def test_cache_miss_unknown_key(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "_DB_PATH", tmp_path / "cache.db")
    assert cache_mod.get_cached_ohlcv("NOPE", "2024-01-01", "2024-02-01") is None
