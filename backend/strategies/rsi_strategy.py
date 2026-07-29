# can chop around the bands; kept simple on purpose

import pandas as pd
import ta


def run(df, period=14, overbought=70, oversold=30):
    """rsi signals via ta. 1 / -1 / 0."""
    out = df.copy()
    rsi_series = ta.momentum.RSIIndicator(out["close"], window=period).rsi()
    out["rsi"] = rsi_series
    sig = []
    # level rules - not crossover; can fire many days in a row while stuck in a band
    for v in rsi_series:
        if pd.isna(v):
            sig.append(0)  # warmup bars before rsi exists
        elif v < oversold:
            sig.append(1)
        elif v > overbought:
            sig.append(-1)
        else:
            sig.append(0)
    out["signal"] = sig
    return out
