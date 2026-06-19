"""Persistence for evidence references (the ``evidence_refs`` table).

Reads/writes :class:`~app.models.contracts.EvidenceRef` rows via ``sqlite3``
against ``app.config.DB_PATH`` (overridable for tests). Upserts are keyed on
``(domain, pmid)`` so re-running the evidence layer never creates duplicates;
refs without a PMID (curated free-text claims) are de-duplicated on
``(domain, claim)`` instead.

The schema is defined in ``app/storage/schema.sql`` (owned by the orchestrator).
This module only ensures the single ``evidence_refs`` table exists so it can be
used standalone in tests without running the full schema bootstrap.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from app.config import DB_PATH
from app.models.contracts import EvidenceGrade, EvidenceRef

__all__ = ["init_table", "save_refs", "load_refs", "clear_domain"]

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS evidence_refs (
    id             INTEGER PRIMARY KEY,
    domain         TEXT,
    claim          TEXT,
    pmid           TEXT,
    title          TEXT,
    year           INTEGER,
    source         TEXT,
    evidence_grade TEXT,
    url            TEXT
);
"""


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_table(db_path: str | Path | None = None) -> None:
    """Ensure the ``evidence_refs`` table exists."""
    with _connect(db_path) as conn:
        conn.execute(_CREATE_TABLE)
        conn.commit()


def _existing_id(
    conn: sqlite3.Connection, domain: str, ref: EvidenceRef
) -> int | None:
    """Find a matching row for upsert keyed on (domain, pmid) or (domain, claim)."""
    if ref.pmid:
        row = conn.execute(
            "SELECT id FROM evidence_refs WHERE domain IS ? AND pmid = ?",
            (domain, ref.pmid),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM evidence_refs "
            "WHERE domain IS ? AND pmid IS NULL AND claim = ?",
            (domain, ref.claim),
        ).fetchone()
    return int(row["id"]) if row else None


def save_refs(
    domain: str,
    refs: Iterable[EvidenceRef],
    db_path: str | Path | None = None,
) -> int:
    """Upsert *refs* for *domain*. Returns the number of rows written."""
    init_table(db_path)
    written = 0
    with _connect(db_path) as conn:
        for ref in refs:
            grade = (
                ref.grade.value
                if isinstance(ref.grade, EvidenceGrade)
                else str(ref.grade)
            )
            values = (
                domain,
                ref.claim,
                ref.pmid,
                ref.title,
                ref.year,
                ref.source,
                grade,
                ref.url,
            )
            existing = _existing_id(conn, domain, ref)
            if existing is None:
                conn.execute(
                    "INSERT INTO evidence_refs "
                    "(domain, claim, pmid, title, year, source, "
                    " evidence_grade, url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    values,
                )
            else:
                conn.execute(
                    "UPDATE evidence_refs SET "
                    "claim=?, pmid=?, title=?, year=?, source=?, "
                    "evidence_grade=?, url=? WHERE id=?",
                    (*values[1:], existing),
                )
            written += 1
        conn.commit()
    return written


def load_refs(domain: str, db_path: str | Path | None = None) -> list[EvidenceRef]:
    """Read back all stored refs for *domain* as :class:`EvidenceRef` objects."""
    init_table(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT claim, pmid, title, year, source, evidence_grade, url "
            "FROM evidence_refs WHERE domain IS ? ORDER BY id",
            (domain,),
        ).fetchall()
    refs: list[EvidenceRef] = []
    for row in rows:
        try:
            grade = EvidenceGrade(row["evidence_grade"])
        except ValueError:
            grade = EvidenceGrade.unsupported
        refs.append(
            EvidenceRef(
                claim=row["claim"],
                grade=grade,
                pmid=row["pmid"],
                title=row["title"],
                year=row["year"],
                url=row["url"],
                source=row["source"],
            )
        )
    return refs


def clear_domain(domain: str, db_path: str | Path | None = None) -> int:
    """Delete all refs for *domain*. Returns rows deleted (mainly for tests)."""
    init_table(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM evidence_refs WHERE domain IS ?", (domain,))
        conn.commit()
        return cur.rowcount
