# pipeline lives in strategies + engine

from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from backtester.engine import backtest, buy_hold_curve, price_signals_payload
from data.fetcher import fetch_ohlcv
from data.run_store import get_run, list_runs, save_run
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


def _normalize_strategy(name):
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
    params = body.get("params") or {}

    def pick(key, default):
        if key in body and body[key] is not None:
            return body[key]
        if key in params and params[key] is not None:
            return params[key]
        return default

    return {
        "commission_bps": float(pick("commission_bps", 5)),
        "slippage_bps": float(pick("slippage_bps", 5)),
        "max_drawdown_pct": (float(pick("max_drawdown_pct", 0)) or None),
        "stop_loss_pct": (float(pick("stop_loss_pct", 0)) or None),
        "initial_capital": float(pick("initial_capital", 10000)),
        "position_size_pct": float(pick("position_size_pct", 100)),
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
        walk_forward = bool(params.get("walk_forward", False))
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
    )
    bh = buy_hold_curve(
        df,
        initial_capital=capital,
        commission_bps=costs["commission_bps"],
        slippage_bps=costs["slippage_bps"],
    )
    return bt, bh


def _oos_window(validation):
    # first test_start → last test_end across folds (for chart labels)
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
        ticker = body.get("ticker")
        start = body.get("start")
        end = body.get("end")
        strategy = body.get("strategy")
        params = body.get("params") or {}
        if not ticker or not start or not end:
            return jsonify({"error": "ticker, start, and end are required"}), 400
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

        # same signals, two cost worlds - honesty check for "edge" that dies on fees
        bt, bh = _simulate(df, costs)
        zero_costs = {
            **costs,
            "commission_bps": 0.0,
            "slippage_bps": 0.0,
        }
        bt_zero, bh_zero = _simulate(df, zero_costs)
        oos = _oos_window(validation)

        persist_params = {
            **params,
            "commission_bps": costs["commission_bps"],
            "slippage_bps": costs["slippage_bps"],
            "max_drawdown_pct": costs["max_drawdown_pct"],
            "stop_loss_pct": costs["stop_loss_pct"],
            "initial_capital": costs["initial_capital"],
            "position_size_pct": costs["position_size_pct"],
        }
        meta = {
            "validation": validation,
            "oos_window": oos,
            "costs": {
                "commission_bps": costs["commission_bps"],
                "slippage_bps": costs["slippage_bps"],
                "total_costs": bt.get("total_costs", 0),
                "position_size_pct": costs["position_size_pct"],
            },
            "risk": {
                "max_drawdown_pct": costs["max_drawdown_pct"],
                "stop_loss_pct": costs["stop_loss_pct"],
                "halted": bt.get("halted", False),
                "halt_reason": bt.get("halt_reason"),
                "stop_exits": bt.get("stop_exits", 0),
            },
            "trades": bt.get("trades") or [],
            "metrics_extra": {
                "sortino_ratio": bt.get("sortino_ratio"),
                "avg_win_pct": bt.get("avg_win_pct"),
                "avg_loss_pct": bt.get("avg_loss_pct"),
                "time_in_market": bt.get("time_in_market"),
                "profit_factor": bt.get("profit_factor"),
            },
            "storage": (
                "sqlite run history on purpose - fine for a single-user demo. "
                "postgres would only matter if multiple people hit this at once."
            ),
            "limitations": [
                "Paper backtest only - not live trading advice.",
                "Fills at daily close; real markets have intraday path dependency.",
                "Costs are a simple bps model (commission + slippage), not exchange fees.",
            ],
        }

        run_id = save_run(
            created_at=datetime.now(timezone.utc).isoformat(),
            ticker=str(ticker),
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
            "buy_hold_curve_zero_cost": bh_zero,
            "zero_cost": {
                "total_return": bt_zero["total_return"],
                "sharpe_ratio": bt_zero["sharpe_ratio"],
                "max_drawdown": bt_zero["max_drawdown"],
                "win_rate": bt_zero["win_rate"],
                "num_trades": bt_zero["num_trades"],
                "total_costs": bt_zero.get("total_costs", 0),
            },
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
            "halted": bt.get("halted", False),
            "halt_reason": bt.get("halt_reason"),
            "stop_exits": bt.get("stop_exits", 0),
            "trades": bt.get("trades") or [],
            "validation": validation,
            "oos_window": oos,
            "meta": meta,
        }
        return jsonify(out)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"backtest failed: {e!s}"}), 500


@app.route("/api/runs", methods=["GET"])
def api_runs():
    limit = request.args.get("limit", default=20, type=int)
    ticker = request.args.get("ticker")
    strategy = request.args.get("strategy")
    return jsonify({"runs": list_runs(limit, ticker=ticker, strategy=strategy)})


@app.route("/api/runs/<int:run_id>", methods=["GET"])
def api_run_detail(run_id: int):
    row = get_run(run_id)
    if row is None:
        return jsonify({"error": "run not found"}), 404
    return jsonify(row)


if __name__ == "__main__":
    # 5050 - macos airplay steals 5000 and returns 403 ("tickers: forbidden" via vite proxy)
    app.run(host="0.0.0.0", port=5050, debug=True)
