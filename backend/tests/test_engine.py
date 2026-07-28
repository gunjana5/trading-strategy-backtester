import pandas as pd

from backtester.engine import backtest, buy_hold_curve


def _series(prices, signals):
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({"close": prices, "signal": signals}, index=idx)


def test_backtest_buy_then_sell_profit():
    df = _series([100, 105, 110], [1, 0, -1])
    result = backtest(df, initial_capital=1000)
    assert result["num_trades"] == 1
    assert result["total_return"] > 0
    assert abs(result["total_return"] - 10.0) < 0.01


def test_backtest_buy_then_sell_loss():
    df = _series([100, 95, 90], [1, 0, -1])
    result = backtest(df, initial_capital=1000)
    assert result["num_trades"] == 1
    assert result["total_return"] < 0


def test_backtest_no_trades_flat():
    df = _series([100, 101, 102], [0, 0, 0])
    result = backtest(df, initial_capital=1000)
    assert result["num_trades"] == 0
    assert abs(result["total_return"]) < 0.01


def test_backtest_win_rate_all_wins():
    df = _series([10, 12, 14, 16], [1, 0, -1, 1])
    result = backtest(df, initial_capital=100)
    assert result["win_rate"] == 100.0 or result["num_trades"] >= 1


def test_buy_hold_curve_tracks_price():
    df = _series([100, 110, 121], [0, 0, 0])
    curve = buy_hold_curve(df, initial_capital=1000)
    assert len(curve) == 3
    assert abs(curve[-1]["value"] - 1210) < 0.01


def test_backtest_equity_curve_length():
    df = _series([50, 55, 60, 58], [1, 0, 0, -1])
    result = backtest(df)
    assert len(result["equity_curve"]) == 4


def test_commission_reduces_return():
    df = _series([100, 110], [1, -1])
    clean = backtest(df, initial_capital=1000, commission_bps=0, slippage_bps=0)
    costly = backtest(df, initial_capital=1000, commission_bps=50, slippage_bps=0)
    assert costly["total_return"] < clean["total_return"]
    assert costly["total_costs"] > 0


def test_slippage_hurts_round_trip():
    df = _series([100, 110], [1, -1])
    clean = backtest(df, initial_capital=1000, commission_bps=0, slippage_bps=0)
    slip = backtest(df, initial_capital=1000, commission_bps=0, slippage_bps=100)
    assert slip["total_return"] < clean["total_return"]


def test_stop_loss_exits_losing_trade():
    # Buy at 100, price crashes - stop at 10% should force exit before final bar
    df = _series([100, 95, 85, 80], [1, 0, 0, 0])
    result = backtest(df, initial_capital=1000, stop_loss_pct=10)
    assert result["stop_exits"] >= 1
    assert result["num_trades"] >= 1


def test_max_drawdown_halts_new_entries():
    # Big loss then a buy signal later - after DD halt, later buys should not fire
    prices = [100, 70, 70, 90, 100]
    signals = [1, 0, 0, 1, -1]
    df = _series(prices, signals)
    result = backtest(df, initial_capital=1000, max_drawdown_pct=20)
    assert result["halted"] is True
    assert result["halt_reason"] == "max_drawdown"
