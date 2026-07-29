# normalises column quirks before anything else sees the frame

import pandas as pd
import yfinance as yf

from data.cache import get_cached_ohlcv, set_cached_ohlcv


def fetch_ohlcv(ticker, start, end):
    """ohlcv between start/end; cache first, then yfinance."""
    cached = get_cached_ohlcv(ticker, start, end)
    if cached is not None and not cached.empty:
        return cached

    t = ticker.strip().upper()
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
    if "close" not in out.columns and "adj close" in raw.columns:
        out["close"] = raw["adj close"]
    missing = [c for c in need if c not in out.columns]
    if missing:
        raise ValueError(f"missing columns for {t}: {missing}")
    out = out[need].copy()
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out = out.sort_index()
    out = out.dropna(how="any")
    if out.empty:
        raise ValueError(f"no clean rows for {t} between {start} and {end}")
    out = out.astype(float)
    set_cached_ohlcv(ticker, start, end, out)
    return out
