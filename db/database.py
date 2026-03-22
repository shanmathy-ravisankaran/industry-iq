import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import zoneinfo


DB_PATH = Path(os.getenv("DB_PATH", "./db/history.db"))
CST = zoneinfo.ZoneInfo("America/Chicago")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                industry TEXT NOT NULL,
                brand TEXT NOT NULL,
                avg_score REAL NOT NULL,
                bullish_count INTEGER NOT NULL,
                bearish_count INTEGER NOT NULL,
                neutral_count INTEGER NOT NULL,
                anomaly_count INTEGER NOT NULL,
                forecast_30d REAL,
                insight_report TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_run(
    *,
    industry: str,
    brand: str,
    avg_score: float,
    bullish_count: int,
    bearish_count: int,
    neutral_count: int,
    anomaly_count: int,
    forecast_30d: float | None,
    insight_report: str,
) -> int:
    with get_connection() as conn:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor = conn.execute(
            """
            INSERT INTO runs (
                timestamp,
                industry,
                brand,
                avg_score,
                bullish_count,
                bearish_count,
                neutral_count,
                anomaly_count,
                forecast_30d,
                insight_report
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                industry,
                brand,
                avg_score,
                bullish_count,
                bearish_count,
                neutral_count,
                anomaly_count,
                forecast_30d,
                insight_report,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _to_client_timestamp(raw_timestamp: str) -> str:
    try:
        if raw_timestamp.endswith("Z") or "+" in raw_timestamp[10:]:
            dt = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        else:
            # Older rows were stored as America/Chicago local time without timezone info.
            naive = datetime.strptime(raw_timestamp, "%Y-%m-%d %H:%M:%S")
            dt = naive.replace(tzinfo=CST).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return raw_timestamp


def get_recent_runs(limit: int = 10, brand: str | None = None, industry: str | None = None) -> list[dict]:
    query = """
        SELECT
            id,
            timestamp,
            industry,
            brand,
            avg_score,
            bullish_count,
            bearish_count,
            neutral_count,
            anomaly_count,
            forecast_30d,
            insight_report
        FROM runs
    """
    conditions: list[str] = []
    params: list[object] = []

    if brand:
        conditions.append("brand = ?")
        params.append(brand)
    if industry:
        conditions.append("industry = ?")
        params.append(industry)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    normalized_rows = []
    for row in rows:
        item = dict(row)
        item["timestamp"] = _to_client_timestamp(str(item["timestamp"]))
        normalized_rows.append(item)

    return normalized_rows
