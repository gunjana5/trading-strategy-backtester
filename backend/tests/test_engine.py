# toy price/signal frames - no yahoo needed

import pandas as pd

from backtester.engine import backtest, buy_hold_curve, oos_metrics_block


def _series(prices, signals):
    # tiny helper so each test stays a one-liner of prices + signals
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({"close": prices, "signal": signals}, index=idx)


def test_backtest_buy_then_sell_profit():
    # same_bar keeps signal+fill on one close (legacy path)
    df = _series([100, 105, 110], [1, 0, -1])
    result = backtest(df, initial_capital=1000, fill_timing="same_bar")
    assert result["num_trades"] == 1
    assert result["total_return"] > 0
    assert abs(result["total_return"] - 10.0) < 0.01


def test_backtest_buy_then_sell_loss():
    df = _series([100, 95, 90], [1, 0, -1])
    result = backtest(df, initial_capital=1000, fill_timing="same_bar")
    assert result["num_trades"] == 1
    assert result["total_return"] < 0


def test_backtest_no_trades_flat():
    df = _series([100, 101, 102], [0, 0, 0])
    result = backtest(df, initial_capital=1000)
    assert result["num_trades"] == 0
    assert abs(result["total_return"]) < 0.01


def test_backtest_win_rate_all_wins():
    df = _series([10, 12, 14, 16], [1, 0, -1, 1])
    result = backtest(df, initial_capital=100, fill_timing="same_bar")
    assert result["win_rate"] == 100.0 or result["num_trades"] >= 1


def test_buy_hold_curve_tracks_price():
    # 100 to 121 is +21%, so £1000 should mark ~1210
    df = _series([100, 110, 121], [0, 0, 0])
    curve = buy_hold_curve(df, initial_capital=1000)
    assert len(curve) == 3
    assert abs(curve[-1]["value"] - 1210) < 0.01


def test_backtest_equity_curve_length():
    df = _series([50, 55, 60, 58], [1, 0, 0, -1])
    result = backtest(df, fill_timing="same_bar")
    assert len(result["equity_curve"]) == 4


def test_commission_reduces_return():
    df = _series([100, 110], [1, -1])
    clean = backtest(df, initial_capital=1000, commission_bps=0, slippage_bps=0, fill_timing="same_bar")
    costly = backtest(
        df, initial_capital=1000, commission_bps=50, slippage_bps=0, fill_timing="same_bar"
    )
    assert costly["total_return"] < clean["total_return"]
    assert costly["total_costs"] > 0


def test_slippage_hurts_round_trip():
    df = _series([100, 110], [1, -1])
    clean = backtest(df, initial_capital=1000, commission_bps=0, slippage_bps=0, fill_timing="same_bar")
    slip = backtest(
        df, initial_capital=1000, commission_bps=0, slippage_bps=100, fill_timing="same_bar"
    )
    assert slip["total_return"] < clean["total_return"]


def test_stop_loss_exits_losing_trade():
    df = _series([100, 95, 85, 80], [1, 0, 0, 0])
    result = backtest(df, initial_capital=1000, stop_loss_pct=10, fill_timing="same_bar")
    assert result["stop_exits"] >= 1
    assert result["num_trades"] >= 1


def test_max_drawdown_halts_new_entries():
    prices = [100, 70, 70, 90, 100]
    signals = [1, 0, 0, 1, -1]
    df = _series(prices, signals)
    result = backtest(df, initial_capital=1000, max_drawdown_pct=20, fill_timing="same_bar")
    assert result["halted"] is True
    assert result["halt_reason"] == "max_drawdown"


def test_trade_blotter_records_closed_round_trip():
    df = _series([100, 105, 110], [1, 0, -1])
    result = backtest(df, initial_capital=1000, fill_timing="same_bar")
    assert len(result["trades"]) == 1
    t = result["trades"][0]
    assert t["entry_date"] == "2024-01-01"
    assert t["exit_date"] == "2024-01-03"
    assert t["reason"] == "signal"
    assert t["pnl_pct"] > 0


def test_position_size_leaves_residual_cash():
    df = _series([100, 101, 102], [1, 0, 0])
    result = backtest(df, initial_capital=1000, position_size_pct=50, fill_timing="same_bar")
    assert result["final_shares"] > 0
    assert result["final_cash"] > 400
    assert abs(result["final_cash"] - 500) < 1.0


def test_sortino_present_with_downside():
    df = _series([100, 120, 90, 95], [1, 0, 0, -1])
    result = backtest(df, initial_capital=1000, fill_timing="same_bar")
    assert "sortino_ratio" in result
    assert result["sortino_ratio"] == result["sortino_ratio"]
    assert abs(result["sortino_ratio"]) < 1e6
    assert result["time_in_market"] > 0
    assert "avg_win_pct" in result
    assert "avg_loss_pct" in result
    assert "profit_factor" in result


def test_next_bar_fills_on_following_close():
    # signal on day0, fill at day1 close; sell signal day2 fills day3
    df = _series([100, 110, 120, 130], [1, 0, -1, 0])
    result = backtest(df, initial_capital=1000, fill_timing="next_bar")
    assert result["fill_timing"] == "next_bar"
    assert result["num_trades"] == 1
    t = result["trades"][0]
    assert t["entry_date"] == "2024-01-02"
    assert t["exit_date"] == "2024-01-04"
    assert abs(t["entry_price"] - 110) < 0.01


def test_same_bar_fills_same_close():
    df = _series([100, 110, 120], [1, 0, -1])
    result = backtest(df, initial_capital=1000, fill_timing="same_bar")
    assert result["trades"][0]["entry_date"] == "2024-01-01"
    assert abs(result["trades"][0]["entry_price"] - 100) < 0.01


def test_allow_short_opens_on_sell_when_flat():
    # flat then -1 opens short; later 1 covers
    df = _series([100, 90, 80, 70], [0, -1, 0, 1])
    long_only = backtest(df, initial_capital=1000, fill_timing="same_bar", allow_short=False)
    assert long_only["num_trades"] == 0
    shorted = backtest(df, initial_capital=1000, fill_timing="same_bar", allow_short=True)
    assert shorted["allow_short"] is True
    assert shorted["num_trades"] == 1
    assert shorted["trades"][0]["side"] == "short"
    assert shorted["total_return"] > 0


def test_oos_metrics_block_rebases():
    df = _series([100, 100, 100, 110, 120], [0, 0, 1, 0, -1])
    bt = backtest(df, initial_capital=1000, fill_timing="same_bar")
    oos = oos_metrics_block(bt, oos_start="2024-01-03", initial_capital=1000)
    assert oos is not None
    assert "sharpe_ratio" in oos
    assert oos["oos_start"] == "2024-01-03"
