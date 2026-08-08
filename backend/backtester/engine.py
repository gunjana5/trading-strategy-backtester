# costs + stop loss live here so strategies stay dumb

from __future__ import annotations

import numpy as np
import pandas as pd


def _date_str(idx) -> str:
    return str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]


def _metrics_from_equity(
    equity_series: pd.Series,
    *,
    initial_capital: float,
    trades: list[dict],
    days_invested: int,
    n_bars: int,
    commission_bps: float,
    slippage_bps: float,
    position_size_pct: float,
    halted: bool,
    halt_reason,
    stop_exits: int,
    dd_halts: int,
    total_costs: float,
    cash: float,
    shares: float,
) -> dict:
    # shared headline math for full-run and oos-only slices
    final = float(equity_series.iloc[-1]) if len(equity_series) else float(initial_capital)
    total_return = (final / initial_capital - 1.0) * 100.0
    daily_rets = equity_series.pct_change().dropna()
    if len(daily_rets) > 1 and daily_rets.std() > 1e-12:
        ann_ret = float((1.0 + daily_rets.mean()) ** 252 - 1.0)
        ann_vol = float(daily_rets.std() * np.sqrt(252))
        sharpe_ratio = ann_ret / ann_vol if ann_vol > 1e-12 else 0.0
    else:
        ann_ret = 0.0
        sharpe_ratio = 0.0

    downside = daily_rets[daily_rets < 0]
    if len(daily_rets) > 1 and len(downside) > 0 and downside.std() > 1e-12:
        downside_vol = float(downside.std() * np.sqrt(252))
        sortino_ratio = ann_ret / downside_vol if downside_vol > 1e-12 else 0.0
    elif len(daily_rets) > 1 and (daily_rets >= 0).all():
        sortino_ratio = float(sharpe_ratio) if sharpe_ratio else 0.0
    else:
        sortino_ratio = 0.0

    roll_max = equity_series.cummax()
    dd = (equity_series - roll_max) / roll_max.replace(0, np.nan)
    max_drawdown = float(abs(dd.min()) * 100.0) if len(dd) else 0.0

    win_pnls = [t["pnl_pct"] for t in trades if t.get("pnl_pct", 0) > 0]
    loss_pnls = [t["pnl_pct"] for t in trades if t.get("pnl_pct", 0) < 0]
    closed = len(win_pnls) + len(loss_pnls)
    win_rate = (len(win_pnls) / closed * 100.0) if closed > 0 else 0.0
    avg_win_pct = float(np.mean(win_pnls)) if win_pnls else 0.0
    avg_loss_pct = float(np.mean(loss_pnls)) if loss_pnls else 0.0
    time_in_market = (days_invested / n_bars * 100.0) if n_bars > 0 else 0.0

    gross_profit = 0.0
    gross_loss = 0.0
    for t in trades:
        trade_side = t.get("side", "long")
        shares_abs = abs(float(t.get("shares", 0)))
        fees = float(t.get("fees", 0))
        if trade_side == "short":
            dollar = shares_abs * (t["entry_price"] - t["exit_price"]) - fees
        else:
            dollar = shares_abs * (t["exit_price"] - t["entry_price"]) - fees
        if dollar > 0:
            gross_profit += dollar
        elif dollar < 0:
            gross_loss += abs(dollar)

    if gross_loss > 1e-12:
        profit_factor = float(gross_profit / gross_loss)
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    equity_curve = [
        {"date": _date_str(idx), "value": float(v)} for idx, v in equity_series.items()
    ]
    return {
        "equity_curve": equity_curve,
        "total_return": total_return,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": float(sortino_ratio),
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "time_in_market": float(time_in_market),
        "profit_factor": profit_factor if np.isfinite(profit_factor) else None,
        "num_trades": int(len(trades)),
        "total_costs": float(total_costs),
        "commission_bps": commission_bps,
        "slippage_bps": slippage_bps,
        "position_size_pct": position_size_pct,
        "halted": halted,
        "halt_reason": halt_reason,
        "stop_exits": int(stop_exits),
        "drawdown_halts": int(dd_halts),
        "trades": trades,
        "final_cash": float(cash),
        "final_shares": float(shares),
    }


def oos_metrics_block(
    bt: dict,
    *,
    oos_start: str,
    initial_capital: float,
) -> dict | None:
    # headline metrics from oos_start onward so flat in-sample equity does not dominate
    if not oos_start or not bt.get("equity_curve"):
        return None
    curve = bt["equity_curve"]
    sliced = [p for p in curve if p["date"] >= oos_start]
    if len(sliced) < 2:
        return None
    # rebase: equity at oos_start is the capital for oos return/sharpe
    start_val = float(sliced[0]["value"])
    if start_val <= 0:
        return None
    idx = pd.to_datetime([p["date"] for p in sliced])
    series = pd.Series([float(p["value"]) for p in sliced], index=idx)
    trades = [t for t in (bt.get("trades") or []) if t.get("exit_date", "") >= oos_start]

    final = float(sliced[-1]["value"])
    total_return = (final / start_val - 1.0) * 100.0
    daily_rets = series.pct_change().dropna()
    if len(daily_rets) > 1 and daily_rets.std() > 1e-12:
        ann_ret = float((1.0 + daily_rets.mean()) ** 252 - 1.0)
        ann_vol = float(daily_rets.std() * np.sqrt(252))
        sharpe_ratio = ann_ret / ann_vol if ann_vol > 1e-12 else 0.0
    else:
        ann_ret = 0.0
        sharpe_ratio = 0.0
    downside = daily_rets[daily_rets < 0]
    if len(daily_rets) > 1 and len(downside) > 0 and downside.std() > 1e-12:
        downside_vol = float(downside.std() * np.sqrt(252))
        sortino_ratio = ann_ret / downside_vol if downside_vol > 1e-12 else 0.0
    elif len(daily_rets) > 1 and (daily_rets >= 0).all():
        sortino_ratio = float(sharpe_ratio) if sharpe_ratio else 0.0
    else:
        sortino_ratio = 0.0
    roll_max = series.cummax()
    dd = (series - roll_max) / roll_max.replace(0, np.nan)
    max_drawdown = float(abs(dd.min()) * 100.0) if len(dd) else 0.0
    win_pnls = [t["pnl_pct"] for t in trades if t.get("pnl_pct", 0) > 0]
    loss_pnls = [t["pnl_pct"] for t in trades if t.get("pnl_pct", 0) < 0]
    closed = len(win_pnls) + len(loss_pnls)
    win_rate = (len(win_pnls) / closed * 100.0) if closed > 0 else 0.0
    _ = initial_capital  # kept for call-site clarity
    return {
        "oos_start": oos_start,
        "total_return": total_return,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": float(sortino_ratio),
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "avg_win_pct": float(np.mean(win_pnls)) if win_pnls else 0.0,
        "avg_loss_pct": float(np.mean(loss_pnls)) if loss_pnls else 0.0,
        "num_trades": len(trades),
        "note": (
            "oos-only metrics from equity at oos_start; "
            "full-period headline still includes flat in-sample equity"
        ),
    }


def backtest(
    df,
    initial_capital=10000,
    commission_bps=0.0,
    slippage_bps=0.0,
    max_drawdown_pct=None,
    stop_loss_pct=None,
    position_size_pct=100.0,
    fill_timing: str = "next_bar",
    allow_short: bool = False,
):
    """Sim: 1 buys/covers, -1 sells/shorts (if allow_short). fills at close; next_bar is default."""
    if df is None or df.empty:
        raise ValueError("empty dataframe for backtest")
    if "signal" not in df.columns or "close" not in df.columns:
        raise ValueError("dataframe must have signal and close columns")

    fill_timing = str(fill_timing or "next_bar").strip().lower()
    if fill_timing not in ("next_bar", "same_bar"):
        raise ValueError("fill_timing must be next_bar or same_bar")
    allow_short = bool(allow_short)

    commission_bps = float(commission_bps or 0.0)
    slippage_bps = float(slippage_bps or 0.0)
    position_size_pct = float(position_size_pct if position_size_pct is not None else 100.0)
    if commission_bps < 0 or slippage_bps < 0:
        raise ValueError("commission_bps and slippage_bps must be >= 0")
    if position_size_pct <= 0 or position_size_pct > 100:
        raise ValueError("position_size_pct must be between 0 and 100")
    if max_drawdown_pct is not None:
        max_drawdown_pct = float(max_drawdown_pct)
        if max_drawdown_pct <= 0 or max_drawdown_pct > 100:
            raise ValueError("max_drawdown_pct must be between 0 and 100")
    if stop_loss_pct is not None:
        stop_loss_pct = float(stop_loss_pct)
        if stop_loss_pct <= 0 or stop_loss_pct > 100:
            raise ValueError("stop_loss_pct must be between 0 and 100")

    prices = df["close"].astype(float).values
    raw_signals = df["signal"].values
    dates = df.index
    n = len(df)

    # next_bar: trade today's close using yesterday's signal (last bar signal never fills)
    if fill_timing == "next_bar":
        exec_signals = np.zeros(n, dtype=float)
        if n > 1:
            exec_signals[1:] = raw_signals[:-1]
    else:
        exec_signals = np.asarray(raw_signals, dtype=float)

    cash = float(initial_capital)
    shares = 0.0  # negative = short
    equity = np.zeros(n)
    entry_price = None
    entry_date = None
    entry_fee = 0.0
    side = None  # "long" | "short"
    wins = 0
    losses = 0
    num_trades = 0
    total_costs = 0.0
    halted = False
    halt_reason = None
    peak_equity = float(initial_capital)
    stop_exits = 0
    dd_halts = 0
    days_invested = 0
    trades: list[dict] = []
    win_pnls: list[float] = []
    loss_pnls: list[float] = []
    gross_profit = 0.0
    gross_loss = 0.0

    def _buy_price(raw: float) -> float:
        return raw * (1.0 + slippage_bps / 10_000.0)

    def _sell_price(raw: float) -> float:
        return raw * (1.0 - slippage_bps / 10_000.0)

    def _commission(notional: float) -> float:
        return abs(notional) * (commission_bps / 10_000.0)

    def _record_trade(
        *,
        exit_price: float,
        exit_idx: int,
        reason: str,
        trade_side: str,
        qty: float,
        fees_total: float,
        pnl_pct: float,
        dollar_pnl: float,
    ) -> None:
        nonlocal wins, losses, num_trades, stop_exits, gross_profit, gross_loss
        num_trades += 1
        trades.append(
            {
                "entry_date": entry_date or _date_str(dates[exit_idx]),
                "exit_date": _date_str(dates[exit_idx]),
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "pnl_pct": float(pnl_pct),
                "reason": reason,
                "fees": float(fees_total),
                "shares": float(qty),
                "side": trade_side,
            }
        )
        if dollar_pnl > 0:
            wins += 1
            win_pnls.append(pnl_pct)
            gross_profit += dollar_pnl
        elif dollar_pnl < 0:
            losses += 1
            loss_pnls.append(pnl_pct)
            gross_loss += abs(dollar_pnl)
        if reason == "stop_loss":
            stop_exits += 1

    def _close_long(price: float, exit_idx: int, reason: str = "signal") -> None:
        nonlocal cash, shares, entry_price, entry_date, entry_fee, side, total_costs
        if shares <= 0:
            return
        fill = _sell_price(price)
        proceeds = shares * fill
        fee = _commission(proceeds)
        total_costs += fee
        net = proceeds - fee
        fees_total = float(entry_fee + fee)
        qty = float(shares)
        if entry_price is not None and entry_price > 0:
            pnl_pct = (fill - entry_price) / entry_price * 100.0
            dollar_pnl = qty * (fill - entry_price) - fees_total
            _record_trade(
                exit_price=fill,
                exit_idx=exit_idx,
                reason=reason,
                trade_side="long",
                qty=qty,
                fees_total=fees_total,
                pnl_pct=pnl_pct,
                dollar_pnl=dollar_pnl,
            )
        cash = cash + net
        shares = 0.0
        entry_price = None
        entry_date = None
        entry_fee = 0.0
        side = None

    def _close_short(price: float, exit_idx: int, reason: str = "signal") -> None:
        # cover: buy back abs(shares)
        nonlocal cash, shares, entry_price, entry_date, entry_fee, side, total_costs
        if shares >= 0:
            return
        qty = abs(shares)
        fill = _buy_price(price)
        cost = qty * fill
        fee = _commission(cost)
        total_costs += fee
        fees_total = float(entry_fee + fee)
        if entry_price is not None and entry_price > 0:
            # short pnl: entry (sell) high, exit (buy) low is good
            pnl_pct = (entry_price - fill) / entry_price * 100.0
            dollar_pnl = qty * (entry_price - fill) - fees_total
            _record_trade(
                exit_price=fill,
                exit_idx=exit_idx,
                reason=reason,
                trade_side="short",
                qty=qty,
                fees_total=fees_total,
                pnl_pct=pnl_pct,
                dollar_pnl=dollar_pnl,
            )
        cash = cash - cost - fee
        shares = 0.0
        entry_price = None
        entry_date = None
        entry_fee = 0.0
        side = None

    def _flatten(price: float, exit_idx: int, reason: str) -> None:
        if shares > 0:
            _close_long(price, exit_idx, reason)
        elif shares < 0:
            _close_short(price, exit_idx, reason)

    def _open_long(price: float, i: int) -> None:
        nonlocal cash, shares, entry_price, entry_date, entry_fee, side, total_costs
        fill = _buy_price(price)
        if fill <= 0:
            return
        deploy = cash * (position_size_pct / 100.0)
        fee = _commission(deploy)
        spendable = deploy - fee
        if spendable <= 0:
            return
        shares = spendable / fill
        total_costs += fee
        entry_price = fill
        entry_date = _date_str(dates[i])
        entry_fee = fee
        cash = cash - deploy
        side = "long"

    def _open_short(price: float, i: int) -> None:
        # sell notional against cash; mark-to-market via negative shares
        nonlocal cash, shares, entry_price, entry_date, entry_fee, side, total_costs
        fill = _sell_price(price)
        if fill <= 0:
            return
        deploy = cash * (position_size_pct / 100.0)
        fee = _commission(deploy)
        if deploy - fee <= 0:
            return
        qty = (deploy - fee) / fill
        # proceeds from short sale sit in cash; liability is -qty shares
        cash = cash + (qty * fill) - fee
        shares = -qty
        total_costs += fee
        entry_price = fill
        entry_date = _date_str(dates[i])
        entry_fee = fee
        side = "short"

    for i in range(n):
        price = prices[i]
        if price <= 0 or np.isnan(price):
            equity[i] = cash + shares * (prices[max(0, i - 1)] if i > 0 else 0.0)
            continue

        # stop-loss before new signals
        if not halted and stop_loss_pct is not None and entry_price is not None and entry_price > 0:
            if shares > 0:
                unrealised = (price - entry_price) / entry_price * 100.0
                if unrealised <= -stop_loss_pct:
                    _close_long(price, i, reason="stop_loss")
            elif shares < 0:
                unrealised = (entry_price - price) / entry_price * 100.0
                if unrealised <= -stop_loss_pct:
                    _close_short(price, i, reason="stop_loss")

        mark = cash + shares * price
        peak_equity = max(peak_equity, mark)
        dd_pct = (peak_equity - mark) / peak_equity * 100.0 if peak_equity > 0 else 0.0
        if not halted and max_drawdown_pct is not None and dd_pct >= max_drawdown_pct:
            _flatten(price, i, reason="max_drawdown")
            halted = True
            halt_reason = "max_drawdown"
            dd_halts += 1

        sig = 0 if halted else int(exec_signals[i]) if not np.isnan(exec_signals[i]) else 0

        if sig == 1:
            if shares < 0:
                _close_short(price, i, reason="signal")
            if shares == 0 and cash > 0:
                _open_long(price, i)
        elif sig == -1:
            if shares > 0:
                _close_long(price, i, reason="signal")
            elif shares == 0 and allow_short and cash > 0:
                _open_short(price, i)

        if shares != 0:
            days_invested += 1

        equity[i] = cash + shares * price
        peak_equity = max(peak_equity, equity[i])

    equity_series = pd.Series(equity, index=dates)
    return _metrics_from_equity(
        equity_series,
        initial_capital=float(initial_capital),
        trades=trades,
        days_invested=days_invested,
        n_bars=n,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        position_size_pct=position_size_pct,
        halted=halted,
        halt_reason=halt_reason,
        stop_exits=stop_exits,
        dd_halts=dd_halts,
        total_costs=total_costs,
        cash=cash,
        shares=shares,
    ) | {
        "fill_timing": fill_timing,
        "allow_short": allow_short,
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
        out.append({"date": _date_str(idx), "value": float(val)})
    return out


def price_signals_payload(df):
    """{date, close, signal} rows for the signal chart."""
    rows = []
    for idx, row in df.iterrows():
        c = float(row["close"])
        s = int(row["signal"]) if not pd.isna(row["signal"]) else 0
        rows.append({"date": _date_str(idx), "close": c, "signal": s})
    return rows
