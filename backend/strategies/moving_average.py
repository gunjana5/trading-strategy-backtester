# signal only - engine decides flatten vs short on -1

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
            sig[i] = -1  # cross down
        else:
            sig[i] = 0
    out["signal"] = sig
    return out


def sensitivity_grid(df, fast_slow_pairs):
    # signal counts for the ma sensitivity table - same fast < slow rule as app.py
    rows = []
    for fast, slow in fast_slow_pairs:
        fast = int(fast)
        slow = int(slow)
        if fast >= slow:
            raise ValueError("fast period must be smaller than slow period")
        if fast < 2 or slow < 3:
            raise ValueError("moving average periods must be at least 2 and 3")
        out = run(df, fast=fast, slow=slow)
        sig = out["signal"]
        rows.append(
            {
                "fast": fast,
                "slow": slow,
                "buy_signals": int((sig == 1).sum()),
                "sell_signals": int((sig == -1).sum()),
            }
        )
    return rows
