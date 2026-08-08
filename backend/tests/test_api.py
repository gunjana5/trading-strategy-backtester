# flask routes with mocked yahoo - never hits the network

import numpy as np
import pandas as pd
import pytest

import app as app_module
from data import run_store


def _fake_ohlcv(n=220, seed=1):
    # ~220 bars so walk-forward still has ~80+ clean rows after feature warm-up
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0, 1, size=n))
    close = np.maximum(close, 5)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, size=n),
        },
        index=idx,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    # temp run db + fake fetch so ci stays offline
    monkeypatch.setattr(run_store, "_DB_PATH", tmp_path / "runs.db")
    monkeypatch.setattr(app_module, "fetch_ohlcv", lambda *a, **k: _fake_ohlcv())
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_health_and_tickers(client):
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.get_json()["ok"] is True
    t = client.get("/api/tickers")
    assert t.status_code == 200
    assert "aapl" in t.get_json()["tickers"]


def test_backtest_missing_body(client):
    res = client.post("/api/backtest", json=None)
    assert res.status_code == 400


def test_backtest_missing_fields(client):
    res = client.post("/api/backtest", json={"ticker": "aapl"})
    assert res.status_code == 400
    assert "required" in res.get_json()["error"]


def test_backtest_bad_strategy(client):
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "not_a_real_strategy",
        },
    )
    assert res.status_code == 400
    assert "strategy" in res.get_json()["error"]


def test_backtest_bad_dates(client):
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "not-a-date",
            "end": "2024-01-01",
            "strategy": "ma",
        },
    )
    assert res.status_code == 400
    assert "yyyy-mm-dd" in res.get_json()["error"]


def test_backtest_fast_ge_slow(client):
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 50, "slow": 20},
        },
    )
    assert res.status_code == 400
    assert "fast period" in res.get_json()["error"]


def test_backtest_bad_position_size(client):
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "position_size_pct": 0,
        },
    )
    assert res.status_code == 400
    assert "position_size_pct" in res.get_json()["error"]


def test_backtest_happy_path_shape(client):
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 5, "slow": 15},
            "commission_bps": 5,
            "slippage_bps": 5,
        },
    )
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    for key in (
        "run_id",
        "equity_curve",
        "buy_hold_curve",
        "zero_cost",
        "trades",
        "total_return",
        "desk_note",
        "price_series",
    ):
        assert key in body
    assert isinstance(body["run_id"], int)
    assert isinstance(body["equity_curve"], list)
    assert isinstance(body["zero_cost"], dict)


def test_compare_response_shape(client):
    # short series + 2 folds keeps ml walk-forward cheap in ci
    res = client.post(
        "/api/compare",
        json={
            "ticker": "msft",
            "start": "2023-01-01",
            "end": "2024-06-01",
            "params": {
                "fast": 5,
                "slow": 15,
                "period": 14,
                "walk_forward": True,
                "n_folds": 2,
            },
        },
    )
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["ticker"] == "MSFT"
    assert "costs" in body
    assert len(body["rows"]) == 3
    strategies = {row["strategy"] for row in body["rows"]}
    assert strategies == {"ma", "rsi", "ml"}
    for row in body["rows"]:
        for key in (
            "total_return",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "num_trades",
            "total_costs",
        ):
            assert key in row


def test_desk_note_patch_and_404(client):
    bt = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 5, "slow": 15},
        },
    )
    assert bt.status_code == 200
    run_id = bt.get_json()["run_id"]

    ok = client.patch(f"/api/runs/{run_id}/note", json={"note": "fees ate the edge"})
    assert ok.status_code == 200
    assert ok.get_json()["desk_note"] == "fees ate the edge"

    missing = client.patch("/api/runs/999999/note", json={"note": "ghost"})
    assert missing.status_code == 404


def test_desk_note_too_long(client):
    bt = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 5, "slow": 15},
        },
    )
    run_id = bt.get_json()["run_id"]
    res = client.patch(f"/api/runs/{run_id}/note", json={"note": "x" * 501})
    assert res.status_code == 400
    assert "500" in res.get_json()["error"]


def test_ml_walk_forward_default_and_oos_fields(client):
    # omit walk_forward - api default is true
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-06-01",
            "strategy": "ml",
            "params": {"n_folds": 2},
        },
    )
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body.get("validation") is not None
    assert body["validation"]["mode"] == "walk_forward"
    assert body["validation"].get("folds")
    assert body.get("oos_window") is not None
    assert body["oos_window"].get("oos_start")
    assert "oos_metrics" in body
    assert "buy_hold_curve_zero_cost" not in body


def test_bad_ticker_rejected(client):
    res = client.post(
        "/api/backtest",
        json={
            "ticker": "!!!",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 5, "slow": 15},
        },
    )
    assert res.status_code == 400
    assert "ticker" in res.get_json()["error"].lower()


def test_delete_run_and_clear(client):
    bt = client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 5, "slow": 15},
        },
    )
    run_id = bt.get_json()["run_id"]
    deleted = client.delete(f"/api/runs/{run_id}")
    assert deleted.status_code == 200
    missing = client.get(f"/api/runs/{run_id}")
    assert missing.status_code == 404

    client.post(
        "/api/backtest",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "strategy": "ma",
            "params": {"fast": 5, "slow": 15},
        },
    )
    cleared = client.delete("/api/runs")
    assert cleared.status_code == 200
    assert cleared.get_json()["deleted"] >= 1
    listed = client.get("/api/runs")
    assert listed.get_json()["runs"] == []


def test_ma_sensitivity_endpoint(client):
    res = client.post(
        "/api/ma-sensitivity",
        json={
            "ticker": "aapl",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "pairs": [[5, 20], [10, 30]],
        },
    )
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert len(body["rows"]) == 2
    assert "buy_signals" in body["rows"][0]
