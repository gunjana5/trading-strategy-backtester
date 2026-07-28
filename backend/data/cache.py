# ttl is 24h; key = ticker|start|end

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

_DB_PATH = Path(__file__).resolve().parent.parent / "market_cache.db"
_TTL = timedelta(hours=24)  # cache ttl - stale after a day, then refetch


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ohlcv_cache (
            cache_key TEXT PRIMARY KEY,
            fetched_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    return conn


def _cache_key(ticker: str, start: str, end: str) -> str:
    return f"{ticker.strip().upper()}|{start}|{end}"


def get_cached_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame | None:
    key = _cache_key(ticker, start, end)
    with _connect() as conn:
        row = conn.execute(
            "SELECT fetched_at, payload_json FROM ohlcv_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    fetched_at = datetime.fromisoformat(row[0])
    if datetime.now(timezone.utc) - fetched_at.replace(tzinfo=timezone.utc) > _TTL:
        return None
    payload = json.loads(row[1])
    df = pd.DataFrame(payload["rows"])
    df.index = pd.to_datetime(payload["index"])
    return df.astype(float)


def set_cached_ohlcv(ticker: str, start: str, end: str, df: pd.DataFrame) -> None:
    key = _cache_key(ticker, start, end)
    payload = {
        "index": [str(i) for i in df.index],
        "rows": df.reset_index(drop=True).to_dict(orient="records"),
    }
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ohlcv_cache (cache_key, fetched_at, payload_json)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                payload_json = excluded.payload_json
            """,
            (key, now, json.dumps(payload)),
        )
        conn.commit()
