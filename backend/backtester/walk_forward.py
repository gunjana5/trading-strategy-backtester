# each fold only sees past bars; signals outside oos blocks stay 0

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import ta
from sklearn.ensemble import RandomForestClassifier

FEATURE_COLS = [
    "rsi",
    "sma_20",
    "sma_50",
    "macd",
    "volume_change",
    "price_change_1d",
    "price_change_5d",
]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # classic TA stack the forest gets as inputs
    out["rsi"] = ta.momentum.RSIIndicator(out["close"], window=14).rsi()
    out["sma_20"] = ta.trend.SMAIndicator(out["close"], window=20).sma_indicator()
    out["sma_50"] = ta.trend.SMAIndicator(out["close"], window=50).sma_indicator()
    macd_obj = ta.trend.MACD(out["close"])
    out["macd"] = macd_obj.macd()
    out["volume_change"] = out["volume"].pct_change()
    out["price_change_1d"] = out["close"].pct_change()
    out["price_change_5d"] = out["close"].pct_change(5)
    next_ret = out["close"].pct_change().shift(-1)
    # next day up >0.5% counts as "up" - arbitrary but keeps labels less noisy
    out["label"] = (next_ret > 0.005).astype(float)
    out.loc[next_ret.isna(), "label"] = np.nan
    return out


def _clf() -> RandomForestClassifier:
    # fixed seed so reruns on the same window are comparable
    return RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1,
    )


def run_single_split(df: pd.DataFrame, train_frac: float = 0.7) -> tuple[pd.DataFrame, dict[str, Any]]:
    """one chronological 70/30 split - train rows get signal 0 (no pretending)."""
    out = add_features(df)
    m = out.dropna(subset=FEATURE_COLS + ["label"])
    if len(m) < 50:
        raise ValueError("not enough rows after feature engineering for ml strategy (need at least 50)")
    n = len(m)
    split = int(n * train_frac)
    if split < 20 or (n - split) < 5:
        raise ValueError("insufficient data split for training and prediction")
    train = m.iloc[:split]
    test = m.iloc[split:]
    clf = _clf()
    clf.fit(train[FEATURE_COLS].values, train["label"].values.astype(int))
    pred = clf.predict(test[FEATURE_COLS].values)
    # start flat everywhere, then only paint the test window
    out["signal"] = 0
    for idx in train.index:
        out.loc[idx, "signal"] = 0
    for idx, p in zip(test.index, pred):
        # 1 = predicted up so buy; else flatten (-1)
        out.loc[idx, "signal"] = 1 if int(p) == 1 else -1

    # oos label accuracy for the honesty banner - not the same as trading pnl
    y_true = test["label"].values.astype(int)
    acc = float((pred.astype(int) == y_true).mean()) if len(y_true) else 0.0
    meta = {
        "mode": "single_split",
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "oos_accuracy": round(acc, 4),
        "warning": (
            "Single chronological split. In-sample bars are zeroed (no trading). "
            "Metrics reflect the held-out window only, but tuning on this split can still overfit."
        ),
        "folds": [
            {
                "fold": 1,
                "train_end": str(train.index[-1].date()) if hasattr(train.index[-1], "date") else str(train.index[-1])[:10],
                "test_start": str(test.index[0].date()) if hasattr(test.index[0], "date") else str(test.index[0])[:10],
                "test_end": str(test.index[-1].date()) if hasattr(test.index[-1], "date") else str(test.index[-1])[:10],
                "oos_accuracy": round(acc, 4),
                "test_rows": int(len(test)),
            }
        ],
    }
    return out, meta


def run_walk_forward(
    df: pd.DataFrame,
    n_folds: int = 3,
    min_train_rows: int = 60,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """expanding walk-forward: fold k trains on earlier rows, predicts the next block."""
    n_folds = int(n_folds)
    if n_folds < 2 or n_folds > 8:
        raise ValueError("n_folds must be between 2 and 8")

    out = add_features(df)
    m = out.dropna(subset=FEATURE_COLS + ["label"])
    if len(m) < min_train_rows + n_folds * 10:
        raise ValueError(
            f"not enough rows for walk-forward (need ~{min_train_rows + n_folds * 10}+ clean rows)"
        )

    n = len(m)
    # expanding train base, remainder sliced into n_folds test blocks
    test_budget = n - min_train_rows
    fold_size = max(10, test_budget // n_folds)
    out["signal"] = 0
    folds: list[dict[str, Any]] = []
    accuracies: list[float] = []

    for k in range(n_folds):
        # fold k: train = everything before this block; test = next fold_size rows
        test_start = min_train_rows + k * fold_size
        # last fold eats leftover bars so nothing is left unused
        test_end = n if k == n_folds - 1 else min_train_rows + (k + 1) * fold_size
        if test_start >= n or test_end <= test_start:
            break
        train = m.iloc[:test_start]
        test = m.iloc[test_start:test_end]
        if len(train) < min_train_rows or len(test) < 5:
            continue
        clf = _clf()
        clf.fit(train[FEATURE_COLS].values, train["label"].values.astype(int))
        pred = clf.predict(test[FEATURE_COLS].values)
        y_true = test["label"].values.astype(int)
        acc = float((pred.astype(int) == y_true).mean())
        accuracies.append(acc)
        for idx, p in zip(test.index, pred):
            out.loc[idx, "signal"] = 1 if int(p) == 1 else -1
        folds.append(
            {
                "fold": k + 1,
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "train_end": str(train.index[-1].date()) if hasattr(train.index[-1], "date") else str(train.index[-1])[:10],
                "test_start": str(test.index[0].date()) if hasattr(test.index[0], "date") else str(test.index[0])[:10],
                "test_end": str(test.index[-1].date()) if hasattr(test.index[-1], "date") else str(test.index[-1])[:10],
                "oos_accuracy": round(acc, 4),
            }
        )

    if not folds:
        raise ValueError("walk-forward produced no valid folds - try a longer date range")

    mean_acc = float(np.mean(accuracies)) if accuracies else 0.0
    # stitch oos signals across folds - engine sees one continuous signal column
    meta = {
        "mode": "walk_forward",
        "n_folds": len(folds),
        "mean_oos_accuracy": round(mean_acc, 4),
        "oos_accuracy": round(mean_acc, 4),
        "warning": (
            "Walk-forward expanding windows. Each fold trains only on earlier data. "
            "Headline backtest PnL stitches OOS signals - still paper trading, not live edge. "
            "If fold accuracies vary wildly, treat results as unstable / overfit-prone."
        ),
        "folds": folds,
    }
    return out, meta
