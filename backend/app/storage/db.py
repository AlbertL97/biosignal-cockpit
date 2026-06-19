"""SQLite storage helpers.

Creates the database from ``app/storage/schema.sql`` and exposes thin helpers
for connecting, initialising, bulk-inserting, querying, and audit logging.

The DB path comes from :data:`app.config.DB_PATH`. All raw / derived /
interpretation / evidence data live in separate tables (see ``schema.sql``).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_conn(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with row access by name and FKs enabled.

    Args:
        db_path: Optional override for the database location. Defaults to
            :data:`app.config.DB_PATH`.

    Returns:
        An open :class:`sqlite3.Connection` whose ``row_factory`` yields
        :class:`sqlite3.Row` objects.
    """
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def connection(db_path: str | Path | None = None):
    """Context manager yielding a connection that commits/rolls back on exit."""
    conn = get_conn(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | Path | None = None) -> None:
    """Create all tables from ``schema.sql`` (idempotent).

    Args:
        db_path: Optional override for the database location.
    """
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connection(db_path) as conn:
        conn.executescript(sql)


def reset_db(db_path: str | Path | None = None) -> None:
    """Drop the database file (if present) and recreate the schema."""
    path = Path(db_path) if db_path is not None else DB_PATH
    if path.exists():
        path.unlink()
    # WAL side-car files.
    for suffix in ("-wal", "-shm"):
        side = path.with_name(path.name + suffix)
        if side.exists():
            side.unlink()
    init_db(path)


def bulk_insert(
    conn: sqlite3.Connection,
    table: str,
    rows: Iterable[Mapping[str, Any]],
    *,
    or_replace: bool = False,
    batch_size: int = 5000,
) -> int:
    """Insert many rows into ``table`` using ``executemany`` in batches.

    Each row is a mapping of column name -> value. All rows must share the same
    key set as the first row.

    Args:
        conn: Open connection (caller controls the transaction).
        table: Target table name.
        rows: Iterable of column->value mappings.
        or_replace: Emit ``INSERT OR REPLACE`` instead of plain ``INSERT``.
        batch_size: Number of rows per ``executemany`` flush.

    Returns:
        Number of rows inserted.
    """
    it = iter(rows)
    try:
        first = next(it)
    except StopIteration:
        return 0

    columns = list(first.keys())
    placeholders = ", ".join(["?"] * len(columns))
    col_sql = ", ".join(columns)
    verb = "INSERT OR REPLACE" if or_replace else "INSERT"
    stmt = f"{verb} INTO {table} ({col_sql}) VALUES ({placeholders})"  # noqa: S608

    total = 0
    batch: list[Sequence[Any]] = [tuple(first[c] for c in columns)]
    for row in it:
        batch.append(tuple(row[c] for c in columns))
        if len(batch) >= batch_size:
            conn.executemany(stmt, batch)
            total += len(batch)
            batch = []
    if batch:
        conn.executemany(stmt, batch)
        total += len(batch)
    return total


def query(
    conn: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | Mapping[str, Any] = (),
) -> list[sqlite3.Row]:
    """Run a SELECT and return all rows."""
    cur = conn.execute(sql, params)
    return cur.fetchall()


def query_one(
    conn: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | Mapping[str, Any] = (),
) -> sqlite3.Row | None:
    """Run a SELECT and return the first row, or ``None``."""
    cur = conn.execute(sql, params)
    return cur.fetchone()


def execute(
    conn: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | Mapping[str, Any] = (),
) -> int:
    """Run a write statement; return ``cursor.rowcount``."""
    cur = conn.execute(sql, params)
    return cur.rowcount


def audit(conn: sqlite3.Connection, event: str, detail: str = "") -> None:
    """Append an entry to ``audit_log`` (task §12.6 / §13).

    Args:
        conn: Open connection.
        event: Short event key, e.g. ``"ingest.apple_health"``.
        detail: Free-text detail (counts, file paths, errors).
    """
    conn.execute(
        "INSERT INTO audit_log (ts, event, detail) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), event, detail),
    )


def table_count(conn: sqlite3.Connection, table: str) -> int:
    """Return the row count of ``table`` (0 if the table is empty)."""
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()  # noqa: S608
    return int(row["n"]) if row else 0
