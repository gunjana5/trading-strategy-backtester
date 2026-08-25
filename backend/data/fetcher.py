# normalises column quirks before anything else sees the frame

from pathlib import Path

import pandas as pd
import yfinance as yf

from data.cache import get_cached_ohlcv, set_cached_ohlcv

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "demo_ohlcv.csv"


def _load_demo_fixture(start, end) -> pd.DataFrame:
    # synthetic paper series - no yahoo. used when ticker is DEMO
    if not _FIXTURE.is_file():
        raise ValueError("demo fixture missing - expected data/fixtures/demo_ohlcv.csv")
    raw = pd.read_csv(_FIXTURE)
    need = ["open", "high", "low", "close", "volume"]
    if "date" not in raw.columns:
        raise ValueError("demo fixture needs a date column")
    missing = [c for c in need if c not in raw.columns]
    if missing:
        raise ValueError(f"demo fixture missing columns: {missing}")
    out = raw[need].copy()
    out.index = pd.to_datetime(raw["date"])
    out.index.name = None
    out = out.sort_index().astype(float)
    # honour start/end the same way yahoo callers do
    start_s = str(start)[:10] if start else None
    end_s = str(end)[:10] if end else None
    if start_s:
        out = out[out.index >= pd.Timestamp(start_s)]
    if end_s:
        out = out[out.index <= pd.Timestamp(end_s)]
    out = out.dropna(how="any")
    if out.empty:
        raise ValueError(f"no demo rows between {start} and {end}")
    return out


def fetch_ohlcv(ticker, start, end):
    """ohlcv between start/end; DEMO uses local fixture, else cache then yfinance."""
    t = str(ticker).strip().upper()
    if t == "DEMO":
        return _load_demo_fixture(start, end)

    cached = get_cached_ohlcv(ticker, start, end)
    if cached is not None and not cached.empty:
        return cached

    # progress=False or yfinance spam fills the flask logs
    raw = yf.download(t, start=start, end=end, progress=False, auto_adjust=False)
    if raw is None or raw.empty:
        raise ValueError(f"no data returned for {t} between {start} and {end}")
    # yahoo sometimes hands back multiindex / weird casing
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [str(c[0]).lower() for c in raw.columns]
    else:
        raw.columns = [str(c).lower() for c in raw.columns]
    need = ["open", "high", "low", "close", "volume"]
    out = pd.DataFrame(index=raw.index)
    for name in need:
        if name in raw.columns:
            out[name] = raw[name]
    # fallback if close missing but adj close exists
    if "close" not in out.columns and "adj close" in raw.columns:
        out["close"] = raw["adj close"]
    missing = [c for c in need if c not in out.columns]
    if missing:
        raise ValueError(f"missing columns for {t}: {missing}")
    out = out[need].copy()
    # strip tz so date joins / chart labels stay simple
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out = out.sort_index()
    out = out.dropna(how="any")
    if out.empty:
        raise ValueError(f"no clean rows for {t} between {start} and {end}")
    out = out.astype(float)
    set_cached_ohlcv(ticker, start, end, out)
    return out
