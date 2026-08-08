# run_store save/list/get/note/delete - temp db only

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
