# run_store save/list/get/note/delete - temp db only

import pandas as pd

from backtester.engine import backtest
from data import run_store


def _metrics(**kwargs):
    base = {
        "total_return": 1.0,
        "sharpe_ratio": 0.5,
        "max_drawdown": 2.0,
        "win_rate": 50.0,
        "num_trades": 1,
        "total_costs": 0.1,
    }
    base.update(kwargs)
    return base


def test_save_list_get(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "_DB_PATH", tmp_path / "runs.db")
    rid = run_store.save_run(
        created_at="2026-01-01T00:00:00Z",
        ticker="aapl",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="ma",
        params={"fast": 5},
        metrics=_metrics(),
        meta={"desk_note": ""},
        equity_curve=[{"date": "2024-01-01", "value": 100}],
        buy_hold_curve=[{"date": "2024-01-01", "value": 100}],
    )
    assert rid >= 1
    listed = run_store.list_runs(10)
    assert len(listed) == 1
    assert listed[0]["ticker"] == "AAPL"
    row = run_store.get_run(rid)
    assert row is not None
    assert row["equity_curve"][0]["value"] == 100
    assert row["params"]["fast"] == 5


def test_list_filter_ticker(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "_DB_PATH", tmp_path / "runs.db")
    run_store.save_run(
        created_at="2026-01-01T00:00:00Z",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="ma",
        params={},
        metrics=_metrics(),
        meta={},
    )
    run_store.save_run(
        created_at="2026-01-02T00:00:00Z",
        ticker="MSFT",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="rsi",
        params={},
        metrics=_metrics(total_return=2.0),
        meta={},
    )
    only = run_store.list_runs(10, ticker="msft")
    assert len(only) == 1
    assert only[0]["ticker"] == "MSFT"


def test_delete_and_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "_DB_PATH", tmp_path / "runs.db")
    a = run_store.save_run(
        created_at="2026-01-01T00:00:00Z",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="ma",
        params={},
        metrics=_metrics(),
        meta={},
    )
    b = run_store.save_run(
        created_at="2026-01-02T00:00:00Z",
        ticker="MSFT",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="ma",
        params={},
        metrics=_metrics(),
        meta={},
    )
    assert run_store.delete_run(a) is True
    assert run_store.get_run(a) is None
    assert run_store.delete_run(99999) is False
    n = run_store.clear_runs()
    assert n == 1
    assert run_store.get_run(b) is None


def test_update_run_note(tmp_path, monkeypatch):
    # point store at a temp db - leave the real backtest_runs.db alone
    monkeypatch.setattr(run_store, "_DB_PATH", tmp_path / "runs.db")
    rid = run_store.save_run(
        created_at="2026-01-01T00:00:00Z",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="ma",
        params={},
        metrics=_metrics(),
        meta={},
        equity_curve=[{"date": "2024-01-01", "value": 100}],
        buy_hold_curve=[{"date": "2024-01-01", "value": 100}],
    )
    row = run_store.update_run_note(rid, "costs ate the edge")
    assert row is not None
    assert row["meta"]["desk_note"] == "costs ate the edge"


def test_meta_round_trips_price_series(tmp_path, monkeypatch):
    # reopen from history needs price_series still inside meta_json
    monkeypatch.setattr(run_store, "_DB_PATH", tmp_path / "runs.db")
    series = [{"date": "2024-01-02", "close": 101.5, "signal": 1}]
    rid = run_store.save_run(
        created_at="2026-01-01T00:00:00Z",
        ticker="MSFT",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="rsi",
        params={},
        metrics=_metrics(total_return=2.0, sharpe_ratio=0.4, max_drawdown=3.0, win_rate=55.0, num_trades=2, total_costs=0.2),
        meta={
            "price_series": series,
            "equity_curve_zero_cost": [{"date": "2024-01-02", "value": 100}],
            "zero_cost": {"total_return": 2.5, "sharpe_ratio": 0.5},
        },
        equity_curve=[{"date": "2024-01-02", "value": 99}],
        buy_hold_curve=[{"date": "2024-01-02", "value": 100}],
    )
    row = run_store.get_run(rid)
    assert row is not None
    assert row["meta"]["price_series"] == series
    assert row["meta"]["zero_cost"]["total_return"] == 2.5
    assert len(row["meta"]["equity_curve_zero_cost"]) == 1


def test_metric_row_shape_from_engine():
    # engine should always hand back a trades list even for a tiny path
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"close": [100, 105, 110], "signal": [1, 0, -1]}, index=idx)
    bt = backtest(df, initial_capital=1000, fill_timing="same_bar")
    assert "trades" in bt
    assert bt["num_trades"] == 1
