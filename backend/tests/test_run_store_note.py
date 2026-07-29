# smoke test for compare + desk note helpers

import json
from pathlib import Path

import pandas as pd

from backtester.engine import backtest
from data import run_store


def test_update_run_note(tmp_path, monkeypatch):
    # point store at a temp db so we dont touch the real backtest_runs.db
    db = tmp_path / "runs.db"
    monkeypatch.setattr(run_store, "_DB_PATH", db)
    rid = run_store.save_run(
        created_at="2026-01-01T00:00:00Z",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-06-01",
        strategy="ma",
        params={},
        metrics={
            "total_return": 1.0,
            "sharpe_ratio": 0.5,
            "max_drawdown": 2.0,
            "win_rate": 50.0,
            "num_trades": 1,
            "total_costs": 0.1,
        },
        meta={},
        equity_curve=[{"date": "2024-01-01", "value": 100}],
        buy_hold_curve=[{"date": "2024-01-01", "value": 100}],
    )
    row = run_store.update_run_note(rid, "costs ate the edge")
    assert row is not None
    assert row["meta"]["desk_note"] == "costs ate the edge"


def test_metric_row_shape_from_engine():
    # engine should always hand back a trades list even for a tiny path
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"close": [100, 105, 110], "signal": [1, 0, -1]}, index=idx)
    bt = backtest(df, initial_capital=1000)
    assert "trades" in bt
    assert bt["num_trades"] == 1
