# pipeline lives in strategies + engine

import re
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from backtester.engine import backtest, buy_hold_curve, oos_metrics_block, price_signals_payload
from data.fetcher import fetch_ohlcv
from data.run_store import (
    clear_runs,
    delete_run,
    get_run,
    list_runs,
    save_run,
    update_run_note,
)
from strategies import ml_strategy, moving_average, rsi_strategy

app = Flask(__name__)
CORS(app)

TICKERS = [
    "aapl",
    "tsla",
    "msft",
    "googl",
    "amzn",
    "meta",
    "nvda",
    "spy",
    "qqq",
    "btc-usd",
    "eth-usd",
    "jpm",
    "gs",
    "nflx",
    "dis",
    "ba",
    "gm",
    "f",
    "xom",
    "brk-b",
]

# yahoo-ish symbols: letters, digits, dot, hyphen, caret, equals
_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-^=]{1,32}$")


def _normalize_ticker(raw) -> str:
    if raw is None:
        raise ValueError("ticker is required")
    t = str(raw).strip().upper()
    if not t or not _TICKER_RE.match(t):
        raise ValueError(
            "ticker must be 1-32 chars: letters, digits, '.', '-', '^', or '='"
        )
    return t


def _normalize_strategy(name):
    # frontend sends long names; engine keys are short (ma/rsi/ml)
    if not name:
        return None
    s = str(name).lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "moving_average_crossover": "ma",
        "moving_average": "ma",
        "rsi_strategy": "rsi",
        "ml_signal": "ml",
    }
    if s in aliases:
        return aliases[s]
    if s in ("ma", "rsi", "ml"):
        return s
    return None


def _cost_risk_from_body(body: dict) -> dict:
    # costs can sit top-level or inside params - accept both so the ui stays flexible
    params = body.get("params") or {}

    def pick(key, default):
        if key in body and body[key] is not None:
            return body[key]
        if key in params and params[key] is not None:
            return params[key]
        return default

    fill_timing = str(pick("fill_timing", "next_bar")).strip().lower()
    if fill_timing not in ("next_bar", "same_bar"):
        raise ValueError("fill_timing must be next_bar or same_bar")

    return {
        "commission_bps": float(pick("commission_bps", 5)),
        "slippage_bps": float(pick("slippage_bps", 5)),
        "max_drawdown_pct": (float(pick("max_drawdown_pct", 0)) or None),
        "stop_loss_pct": (float(pick("stop_loss_pct", 0)) or None),
        "initial_capital": float(pick("initial_capital", 10000)),
        "position_size_pct": float(pick("position_size_pct", 100)),
        "fill_timing": fill_timing,
        "allow_short": bool(pick("allow_short", False)),
    }


def _apply_strategy(df, strategy_key, params):
    # signals once - then we can backtest with/without costs on the same df
    params = params or {}
    validation = None

    if strategy_key == "ma":
        fast = int(params.get("fast", 20))
        slow = int(params.get("slow", 50))
        if fast >= slow:
            raise ValueError("fast period must be smaller than slow period")
        if fast < 2 or slow < 3:
            raise ValueError("moving average periods must be at least 2 and 3")
        df = moving_average.run(df, fast=fast, slow=slow)
    elif strategy_key == "rsi":
        period = int(params.get("period", 14))
        overbought = float(params.get("overbought", 70))
        oversold = float(params.get("oversold", 30))
        if oversold >= overbought:
            raise ValueError("oversold threshold must be below overbought threshold")
        if period < 2:
            raise ValueError("rsi period must be at least 2")
        df = rsi_strategy.run(df, period=period, overbought=overbought, oversold=oversold)
    elif strategy_key == "ml":
        # default true - matches ui walk-forward checkbox
        walk_forward = bool(params.get("walk_forward", True))
        n_folds = int(params.get("n_folds", 3))
        df, validation = ml_strategy.run(df, walk_forward=walk_forward, n_folds=n_folds)
    else:
        raise ValueError("unknown strategy")
    return df, validation


def _simulate(df, costs):
    capital = costs["initial_capital"]
    bt = backtest(
        df,
        initial_capital=capital,
        commission_bps=costs["commission_bps"],
        slippage_bps=costs["slippage_bps"],
        max_drawdown_pct=costs["max_drawdown_pct"],
        stop_loss_pct=costs["stop_loss_pct"],
        position_size_pct=costs.get("position_size_pct", 100),
        fill_timing=costs.get("fill_timing", "next_bar"),
        allow_short=costs.get("allow_short", False),
    )
    bh = buy_hold_curve(
        df,
        initial_capital=capital,
        commission_bps=costs["commission_bps"],
        slippage_bps=costs["slippage_bps"],
    )
    return bt, bh


def _oos_window(validation):
    if not validation or not validation.get("folds"):
        return None
    folds = validation["folds"]
    return {
        "train_end": folds[0].get("train_end"),
        "oos_start": folds[0].get("test_start"),
        "oos_end": folds[-1].get("test_end"),
        "label": "OOS only - train bars have signal 0 (no trades)",
    }


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"ok": True, "service": "trading-strategy-backtester"})


@app.route("/api/tickers", methods=["GET"])
def api_tickers():
    return jsonify({"tickers": TICKERS})


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    try:
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"error": "expected json body with ticker, start, end, strategy, params"}), 400
        start = body.get("start")
        end = body.get("end")
        strategy = body.get("strategy")
        params = body.get("params") or {}
        if not body.get("ticker") or not start or not end:
            return jsonify({"error": "ticker, start, and end are required"}), 400
        ticker = _normalize_ticker(body.get("ticker"))
        sk = _normalize_strategy(strategy)
        if not sk:
            return jsonify(
                {
                    "error": "strategy must be one of: moving average crossover, rsi strategy, ml signal",
                }
            ), 400
        try:
            datetime.strptime(str(start)[:10], "%Y-%m-%d")
            datetime.strptime(str(end)[:10], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "start and end must be valid dates (yyyy-mm-dd)"}), 400

        costs = _cost_risk_from_body(body)
        if costs["max_drawdown_pct"] is not None and costs["max_drawdown_pct"] <= 0:
            costs["max_drawdown_pct"] = None
        if costs["stop_loss_pct"] is not None and costs["stop_loss_pct"] <= 0:
            costs["stop_loss_pct"] = None
        if costs["position_size_pct"] <= 0 or costs["position_size_pct"] > 100:
            return jsonify({"error": "position_size_pct must be between 0 and 100"}), 400

        df = fetch_ohlcv(ticker, start, end)
        df, validation = _apply_strategy(df, sk, params)
        series = price_signals_payload(df)

        bt, bh = _simulate(df, costs)
        zero_costs = {
            **costs,
            "commission_bps": 0.0,
            "slippage_bps": 0.0,
        }
        bt_zero, _bh_zero = _simulate(df, zero_costs)
        oos = _oos_window(validation)
        oos_metrics = None
        if oos and oos.get("oos_start"):
            oos_metrics = oos_metrics_block(
                bt, oos_start=oos["oos_start"], initial_capital=costs["initial_capital"]
            )

        persist_params = {
            **params,
            "commission_bps": costs["commission_bps"],
            "slippage_bps": costs["slippage_bps"],
            "max_drawdown_pct": costs["max_drawdown_pct"],
            "stop_loss_pct": costs["stop_loss_pct"],
            "initial_capital": costs["initial_capital"],
            "position_size_pct": costs["position_size_pct"],
            "fill_timing": costs["fill_timing"],
            "allow_short": costs["allow_short"],
        }
        zero_cost = {
            "total_return": bt_zero["total_return"],
            "sharpe_ratio": bt_zero["sharpe_ratio"],
            "max_drawdown": bt_zero["max_drawdown"],
            "win_rate": bt_zero["win_rate"],
            "num_trades": bt_zero["num_trades"],
            "total_costs": bt_zero.get("total_costs", 0),
        }
        meta = {
            "validation": validation,
            "oos_window": oos,
            "oos_metrics": oos_metrics,
            "costs": {
                "commission_bps": costs["commission_bps"],
                "slippage_bps": costs["slippage_bps"],
                "total_costs": bt.get("total_costs", 0),
                "position_size_pct": costs["position_size_pct"],
                "fill_timing": costs["fill_timing"],
                "allow_short": costs["allow_short"],
            },
            "risk": {
                "max_drawdown_pct": costs["max_drawdown_pct"],
                "stop_loss_pct": costs["stop_loss_pct"],
                "halted": bt.get("halted", False),
                "halt_reason": bt.get("halt_reason"),
                "stop_exits": bt.get("stop_exits", 0),
            },
            "trades": bt.get("trades") or [],
            "desk_note": "",
            "metrics_extra": {
                "sortino_ratio": bt.get("sortino_ratio"),
                "avg_win_pct": bt.get("avg_win_pct"),
                "avg_loss_pct": bt.get("avg_loss_pct"),
                "time_in_market": bt.get("time_in_market"),
                "profit_factor": bt.get("profit_factor"),
            },
            "price_series": series,
            "equity_curve_zero_cost": bt_zero["equity_curve"],
            "zero_cost": zero_cost,
            "storage": (
                "sqlite run history on purpose - fine for a single-user demo. "
                "postgres would only matter if multiple people hit this at once."
            ),
            "limitations": [
                "Paper backtest only - not live trading advice.",
                "Default fills next bar close; same-bar mode still available.",
                "Costs are a simple bps model (commission + slippage), not exchange fees.",
            ],
        }

        run_id = save_run(
            created_at=datetime.now(timezone.utc).isoformat(),
            ticker=ticker,
            start_date=str(start)[:10],
            end_date=str(end)[:10],
            strategy=sk,
            params=persist_params,
            metrics=bt,
            meta=meta,
            equity_curve=bt["equity_curve"],
            buy_hold_curve=bh,
        )
        out = {
            "run_id": run_id,
            "equity_curve": bt["equity_curve"],
            "buy_hold_curve": bh,
            "equity_curve_zero_cost": bt_zero["equity_curve"],
            "zero_cost": zero_cost,
            "price_series": series,
            "total_return": bt["total_return"],
            "sharpe_ratio": bt["sharpe_ratio"],
            "sortino_ratio": bt.get("sortino_ratio"),
            "max_drawdown": bt["max_drawdown"],
            "win_rate": bt["win_rate"],
            "avg_win_pct": bt.get("avg_win_pct"),
            "avg_loss_pct": bt.get("avg_loss_pct"),
            "time_in_market": bt.get("time_in_market"),
            "profit_factor": bt.get("profit_factor"),
            "num_trades": bt["num_trades"],
            "total_costs": bt.get("total_costs", 0),
            "commission_bps": bt.get("commission_bps", 0),
            "slippage_bps": bt.get("slippage_bps", 0),
            "position_size_pct": bt.get("position_size_pct", 100),
            "fill_timing": costs["fill_timing"],
            "allow_short": costs["allow_short"],
            "halted": bt.get("halted", False),
            "halt_reason": bt.get("halt_reason"),
            "stop_exits": bt.get("stop_exits", 0),
            "trades": bt.get("trades") or [],
            "desk_note": "",
            "validation": validation,
            "oos_window": oos,
            "oos_metrics": oos_metrics,
            "meta": meta,
        }
        return jsonify(out)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "backtest failed"}), 500


@app.route("/api/runs", methods=["GET"])
def api_runs():
    limit = request.args.get("limit", default=20, type=int)
    ticker = request.args.get("ticker")
    strategy = request.args.get("strategy")
    return jsonify({"runs": list_runs(limit, ticker=ticker, strategy=strategy)})


@app.route("/api/runs", methods=["DELETE"])
def api_runs_clear():
    # wipe history - single-user demo
    n = clear_runs()
    return jsonify({"ok": True, "deleted": n})


@app.route("/api/runs/<int:run_id>", methods=["GET"])
def api_run_detail(run_id: int):
    row = get_run(run_id)
    if row is None:
        return jsonify({"error": "run not found"}), 404
    return jsonify(row)


@app.route("/api/runs/<int:run_id>", methods=["DELETE"])
def api_run_delete(run_id: int):
    ok = delete_run(run_id)
    if not ok:
        return jsonify({"error": "run not found"}), 404
    return jsonify({"ok": True, "id": run_id})


@app.route("/api/runs/<int:run_id>/note", methods=["PATCH", "POST"])
def api_run_note(run_id: int):
    try:
        body = request.get_json(silent=True) or {}
        note = body.get("note", "")
        row = update_run_note(run_id, note)
        if row is None:
            return jsonify({"error": "run not found"}), 404
        return jsonify({"id": row["id"], "desk_note": (row.get("meta") or {}).get("desk_note", "")})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "could not save note"}), 500


@app.route("/api/ma-sensitivity", methods=["POST"])
def api_ma_sensitivity():
    # thin wrap over moving_average.sensitivity_grid - signal counts only
    try:
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"error": "expected json body with ticker, start, end"}), 400
        if not body.get("ticker") or not body.get("start") or not body.get("end"):
            return jsonify({"error": "ticker, start, and end are required"}), 400
        ticker = _normalize_ticker(body.get("ticker"))
        start = body.get("start")
        end = body.get("end")
        try:
            datetime.strptime(str(start)[:10], "%Y-%m-%d")
            datetime.strptime(str(end)[:10], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "start and end must be valid dates (yyyy-mm-dd)"}), 400

        pairs = body.get("pairs")
        if not pairs:
            # small default grid
            pairs = [(5, 20), (10, 30), (20, 50), (50, 200)]
        cleaned = []
        for p in pairs:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                raise ValueError("pairs must be a list of [fast, slow]")
            cleaned.append((int(p[0]), int(p[1])))

        df = fetch_ohlcv(ticker, start, end)
        rows = moving_average.sensitivity_grid(df, cleaned)
        return jsonify(
            {
                "ticker": ticker,
                "start": str(start)[:10],
                "end": str(end)[:10],
                "rows": rows,
            }
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "ma sensitivity failed"}), 500


def _metric_row(sk: str, bt: dict, validation=None) -> dict:
    oos = None
    if validation:
        oos = validation.get("mean_oos_accuracy")
        if oos is None:
            oos = validation.get("oos_accuracy")
    return {
        "strategy": sk,
        "total_return": bt.get("total_return"),
        "sharpe_ratio": bt.get("sharpe_ratio"),
        "sortino_ratio": bt.get("sortino_ratio"),
        "max_drawdown": bt.get("max_drawdown"),
        "win_rate": bt.get("win_rate"),
        "num_trades": bt.get("num_trades"),
        "total_costs": bt.get("total_costs"),
        "time_in_market": bt.get("time_in_market"),
        "profit_factor": bt.get("profit_factor"),
        "halted": bt.get("halted", False),
        "mean_oos_accuracy": oos,
    }


@app.route("/api/compare", methods=["POST"])
def api_compare():
    try:
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"error": "expected json body with ticker, start, end"}), 400
        start = body.get("start")
        end = body.get("end")
        params = body.get("params") or {}
        if not body.get("ticker") or not start or not end:
            return jsonify({"error": "ticker, start, and end are required"}), 400
        ticker = _normalize_ticker(body.get("ticker"))
        try:
            datetime.strptime(str(start)[:10], "%Y-%m-%d")
            datetime.strptime(str(end)[:10], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "start and end must be valid dates (yyyy-mm-dd)"}), 400

        costs = _cost_risk_from_body(body)
        if costs["max_drawdown_pct"] is not None and costs["max_drawdown_pct"] <= 0:
            costs["max_drawdown_pct"] = None
        if costs["stop_loss_pct"] is not None and costs["stop_loss_pct"] <= 0:
            costs["stop_loss_pct"] = None
        if costs["position_size_pct"] <= 0 or costs["position_size_pct"] > 100:
            return jsonify({"error": "position_size_pct must be between 0 and 100"}), 400

        base = fetch_ohlcv(ticker, start, end)
        strategy_params = {
            "ma": {"fast": int(params.get("fast", 20)), "slow": int(params.get("slow", 50))},
            "rsi": {
                "period": int(params.get("period", 14)),
                "overbought": float(params.get("overbought", 70)),
                "oversold": float(params.get("oversold", 30)),
            },
            "ml": {
                "walk_forward": bool(params.get("walk_forward", True)),
                "n_folds": int(params.get("n_folds", 3)),
            },
        }

        rows = []
        for sk in ("ma", "rsi", "ml"):
            df = base.copy()
            df, validation = _apply_strategy(df, sk, strategy_params[sk])
            bt, _bh = _simulate(df, costs)
            rows.append(_metric_row(sk, bt, validation))

        return jsonify(
            {
                "ticker": ticker,
                "start": str(start)[:10],
                "end": str(end)[:10],
                "costs": {
                    "commission_bps": costs["commission_bps"],
                    "slippage_bps": costs["slippage_bps"],
                    "position_size_pct": costs["position_size_pct"],
                    "max_drawdown_pct": costs["max_drawdown_pct"],
                    "stop_loss_pct": costs["stop_loss_pct"],
                    "fill_timing": costs["fill_timing"],
                    "allow_short": costs["allow_short"],
                },
                "rows": rows,
            }
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "compare failed"}), 500


if __name__ == "__main__":
    # 5050 - macos airplay steals 5000 and returns 403 ("tickers: forbidden" via vite proxy)
    app.run(host="0.0.0.0", port=5050, debug=True)
