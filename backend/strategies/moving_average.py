# engine is long-only so cross down just means flatten

import pandas as pd


def run(df, fast=20, slow=50):
    """dual sma crossover. 1 = buy, -1 = sell, 0 = hold."""
    out = df.copy()
    # min_periods=window so early bars stay nan until the sma is real
    out["fast_sma"] = out["close"].rolling(window=fast, min_periods=fast).mean()
    out["slow_sma"] = out["close"].rolling(window=slow, min_periods=slow).mean()
    sig = [0] * len(out)
    f = out["fast_sma"].values
    s = out["slow_sma"].values
    # look at yesterday vs today to catch the actual cross event
    for i in range(1, len(out)):
        if pd.isna(f[i]) or pd.isna(s[i]) or pd.isna(f[i - 1]) or pd.isna(s[i - 1]):
            sig[i] = 0
            continue
        if f[i] > s[i] and f[i - 1] <= s[i - 1]:
            sig[i] = 1  # cross up
        elif f[i] < s[i] and f[i - 1] >= s[i - 1]:
            sig[i] = -1  # cross down = flatten in the engine
        else:
            sig[i] = 0
    out["signal"] = sig
    return out
