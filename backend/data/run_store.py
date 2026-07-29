# curves + meta so the ui can reload a run without re-fetching yahoo

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "backtest_runs.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            ticker TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            strategy TEXT NOT NULL,
            params_json TEXT NOT NULL,
            total_return REAL NOT NULL,
            sharpe_ratio REAL NOT NULL,
            max_drawdown REAL NOT NULL,
            win_rate REAL NOT NULL,
            num_trades INTEGER NOT NULL,
            total_costs REAL DEFAULT 0,
            meta_json TEXT DEFAULT '{}',
            equity_json TEXT,
            buy_hold_json TEXT
        )
        """
    )
    # light migrations if an older local db is missing columns
    cols = {row[1] for row in conn.execute("PRAGMA table_info(backtest_runs)").fetchall()}
    if "total_costs" not in cols:
        conn.execute("ALTER TABLE backtest_runs ADD COLUMN total_costs REAL DEFAULT 0")
    if "meta_json" not in cols:
        conn.execute("ALTER TABLE backtest_runs ADD COLUMN meta_json TEXT DEFAULT '{}'")
    if "equity_json" not in cols:
        conn.execute("ALTER TABLE backtest_runs ADD COLUMN equity_json TEXT")
    if "buy_hold_json" not in cols:
        conn.execute("ALTER TABLE backtest_runs ADD COLUMN buy_hold_json TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_ticker ON backtest_runs(ticker)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_strategy ON backtest_runs(strategy)"
    )
    return conn


def save_run(
    *,
    created_at: str,
    ticker: str,
    start_date: str,
    end_date: str,
    strategy: str,
    params: dict,
    metrics: dict,
    meta: dict | None = None,
    equity_curve: list | None = None,
    buy_hold_curve: list | None = None,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO backtest_runs (
                created_at, ticker, start_date, end_date, strategy, params_json,
                total_return, sharpe_ratio, max_drawdown, win_rate, num_trades,
                total_costs, meta_json, equity_json, buy_hold_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                ticker.upper(),
                start_date,
                end_date,
                strategy,
                json.dumps(params or {}),
                float(metrics["total_return"]),
                float(metrics["sharpe_ratio"]),
                float(metrics["max_drawdown"]),
                float(metrics["win_rate"]),
                int(metrics["num_trades"]),
                float(metrics.get("total_costs", 0.0)),
                json.dumps(meta or {}),
                json.dumps(equity_curve) if equity_curve is not None else None,
                json.dumps(buy_hold_curve) if buy_hold_curve is not None else None,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def _row_to_summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "ticker": row["ticker"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "strategy": row["strategy"],
        "params": json.loads(row["params_json"] or "{}"),
        "total_return": row["total_return"],
        "sharpe_ratio": row["sharpe_ratio"],
        "max_drawdown": row["max_drawdown"],
        "win_rate": row["win_rate"],
        "num_trades": row["num_trades"],
        "total_costs": row["total_costs"] if row["total_costs"] is not None else 0.0,
        "meta": json.loads(row["meta_json"] or "{}"),
    }


def list_runs(
    limit: int = 20,
    *,
    ticker: str | None = None,
    strategy: str | None = None,
) -> list[dict]:
    limit = max(1, min(limit, 100))  # hard cap so the sidebar never blows up
    clauses = []
    args: list = []
    if ticker:
        clauses.append("ticker = ?")
        args.append(ticker.upper())
    if strategy:
        clauses.append("strategy = ?")
        args.append(strategy.lower())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    args.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, created_at, ticker, start_date, end_date, strategy, params_json,
                   total_return, sharpe_ratio, max_drawdown, win_rate, num_trades,
                   total_costs, meta_json
            FROM backtest_runs
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            args,
        ).fetchall()
    return [_row_to_summary(row) for row in rows]


def get_run(run_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, ticker, start_date, end_date, strategy, params_json,
                   total_return, sharpe_ratio, max_drawdown, win_rate, num_trades,
                   total_costs, meta_json, equity_json, buy_hold_json
            FROM backtest_runs
            WHERE id = ?
            """,
            (int(run_id),),
        ).fetchone()
    if row is None:
        return None
    out = _row_to_summary(row)
    out["equity_curve"] = json.loads(row["equity_json"]) if row["equity_json"] else None
    out["buy_hold_curve"] = json.loads(row["buy_hold_json"]) if row["buy_hold_json"] else None
    return out
