# costs + stop loss live here so strategies stay dumb

from __future__ import annotations

import numpy as np
import pandas as pd


def backtest(
    df,
    initial_capital=10000,
    commission_bps=0.0,
    slippage_bps=0.0,
    max_drawdown_pct=None,
    stop_loss_pct=None,
):
    """Long-only: 1 buys cash at close, -1 flattens, 0 holds. optional costs + risk halts."""
    if df is None or df.empty:
        raise ValueError("empty dataframe for backtest")
    if "signal" not in df.columns or "close" not in df.columns:
        raise ValueError("dataframe must have signal and close columns")

    commission_bps = float(commission_bps or 0.0)
    slippage_bps = float(slippage_bps or 0.0)
    if commission_bps < 0 or slippage_bps < 0:
        raise ValueError("commission_bps and slippage_bps must be >= 0")
    if max_drawdown_pct is not None:
        max_drawdown_pct = float(max_drawdown_pct)
        if max_drawdown_pct <= 0 or max_drawdown_pct > 100:
            raise ValueError("max_drawdown_pct must be between 0 and 100")
    if stop_loss_pct is not None:
        stop_loss_pct = float(stop_loss_pct)
        if stop_loss_pct <= 0 or stop_loss_pct > 100:
            raise ValueError("stop_loss_pct must be between 0 and 100")

    prices = df["close"].astype(float).values
    signals = df["signal"].values
    dates = df.index
    n = len(df)
    cash = float(initial_capital)
    shares = 0.0
    equity = np.zeros(n)
    entry_price = None
    wins = 0
    losses = 0
    num_trades = 0
    total_costs = 0.0
    halted = False
    halt_reason = None
    peak_equity = float(initial_capital)
    stop_exits = 0
    dd_halts = 0

    # costs math: fill worse by slippage_bps/1e4; fee = notional * commission_bps/1e4
    def _buy_price(raw: float) -> float:
        return raw * (1.0 + slippage_bps / 10_000.0)

    def _sell_price(raw: float) -> float:
        return raw * (1.0 - slippage_bps / 10_000.0)

    def _commission(notional: float) -> float:
        return abs(notional) * (commission_bps / 10_000.0)

    def _close_position(price: float, reason: str = "signal") -> None:
        nonlocal cash, shares, entry_price, wins, losses, num_trades, total_costs, stop_exits
        if shares <= 0:
            return
        fill = _sell_price(price)
        proceeds = shares * fill
        fee = _commission(proceeds)
        total_costs += fee
        net = proceeds - fee
        if entry_price is not None and entry_price > 0:
            num_trades += 1
            pnl = (fill - entry_price) / entry_price
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            if reason == "stop_loss":
                stop_exits += 1
        cash = net
        shares = 0.0
        entry_price = None

    for i in range(n):
        price = prices[i]
        if price <= 0 or np.isnan(price):
            equity[i] = cash + shares * (prices[max(0, i - 1)] if i > 0 else 0.0)
            continue

        # stop-loss before new signals - exit if unrealised loss hits threshold
        if (
            not halted
            and stop_loss_pct is not None
            and shares > 0
            and entry_price is not None
            and entry_price > 0
        ):
            unrealised = (price - entry_price) / entry_price * 100.0
            if unrealised <= -stop_loss_pct:
                _close_position(price, reason="stop_loss")

        # max dd halt: flatten + no new buys for the rest of the run
        mark = cash + shares * price
        peak_equity = max(peak_equity, mark)
        if peak_equity > 0:
            dd_pct = (peak_equity - mark) / peak_equity * 100.0
        else:
            dd_pct = 0.0
        if (
            not halted
            and max_drawdown_pct is not None
            and dd_pct >= max_drawdown_pct
        ):
            _close_position(price, reason="max_drawdown")
            halted = True
            halt_reason = "max_drawdown"
            dd_halts += 1

        sig = 0 if halted else signals[i]

        if sig == 1 and cash > 0 and shares == 0:
            fill = _buy_price(price)
            if fill <= 0:
                equity[i] = cash
                continue
            fee = _commission(cash)
            spendable = cash - fee
            if spendable <= 0:
                equity[i] = cash
                continue
            shares = spendable / fill
            total_costs += fee
            entry_price = fill
            cash = 0.0
        elif sig == -1 and shares > 0:
            _close_position(price, reason="signal")

        equity[i] = cash + shares * price
        peak_equity = max(peak_equity, equity[i])

    equity_series = pd.Series(equity, index=dates)
    final = float(equity[-1])
    total_return = (final / initial_capital - 1.0) * 100.0
    daily_rets = equity_series.pct_change().dropna()
    if len(daily_rets) > 1 and daily_rets.std() > 1e-12:
        ann_ret = float((1.0 + daily_rets.mean()) ** 252 - 1.0)
        ann_vol = float(daily_rets.std() * np.sqrt(252))
        sharpe_ratio = ann_ret / ann_vol if ann_vol > 1e-12 else 0.0
    else:
        sharpe_ratio = 0.0
    roll_max = equity_series.cummax()
    dd = (equity_series - roll_max) / roll_max.replace(0, np.nan)
    max_drawdown = float(abs(dd.min()) * 100.0) if len(dd) else 0.0
    closed = wins + losses
    win_rate = (wins / closed * 100.0) if closed > 0 else 0.0
    equity_curve = [
        {"date": str(idx.date()) if hasattr(idx, "date") else str(idx)[:10], "value": float(v)}
        for idx, v in equity_series.items()
    ]
    return {
        "equity_curve": equity_curve,
        "total_return": total_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "num_trades": int(num_trades),
        "total_costs": float(total_costs),
        "commission_bps": commission_bps,
        "slippage_bps": slippage_bps,
        "halted": halted,
        "halt_reason": halt_reason,
        "stop_exits": int(stop_exits),
        "drawdown_halts": int(dd_halts),
    }


def buy_hold_curve(df, initial_capital=10000, commission_bps=0.0, slippage_bps=0.0):
    """buy once at first close (same cost model), hold - fair chart baseline."""
    commission_bps = float(commission_bps or 0.0)
    slippage_bps = float(slippage_bps or 0.0)
    prices = df["close"].astype(float)
    first = prices.iloc[0]
    if first <= 0 or np.isnan(first):
        raise ValueError("invalid first close for buy and hold")
    fill = first * (1.0 + slippage_bps / 10_000.0)
    fee = initial_capital * (commission_bps / 10_000.0)
    spendable = initial_capital - fee
    shares = spendable / fill
    out = []
    for idx, price in prices.items():
        if np.isnan(price) or price <= 0:
            continue
        val = shares * price
        out.append(
            {
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx)[:10],
                "value": float(val),
            }
        )
    return out


def price_signals_payload(df):
    """{date, close, signal} rows for the signal chart."""
    rows = []
    for idx, row in df.iterrows():
        c = float(row["close"])
        s = int(row["signal"]) if not pd.isna(row["signal"]) else 0
        d = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
        rows.append({"date": d, "close": c, "signal": s})
    return rows
