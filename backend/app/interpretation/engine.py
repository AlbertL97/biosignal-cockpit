"""Interpretation engine: orchestration, safety filtering, and persistence.

Runs the per-domain ``compute`` functions, passes every piece of generated text
through the safety filter (so banned diagnostic phrasing never reaches the UI or
database), and persists each result to the ``domain_status`` table.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable

from app.interpretation import levers as levers_mod
from app.interpretation import safety
from app.interpretation.context import DataContext
from app.interpretation.domains import (
    brain,
    cardiovascular,
    gut,
    immune_inflammation,
    metabolic,
    musculoskeletal,
    oral_dental,
    sleep_recovery,
    stress_autonomic,
)
from app.models.contracts import DomainStatus

# Canonical domain → compute mapping (ARCHITECTURE.md §3).
DOMAIN_REGISTRY: dict[str, Callable[[DataContext], DomainStatus]] = {
    "gut": gut.compute,
    "brain": brain.compute,
    "cardiovascular": cardiovascular.compute,
    "oral_dental": oral_dental.compute,
    "musculoskeletal": musculoskeletal.compute,
    "metabolic": metabolic.compute,
    "sleep_recovery": sleep_recovery.compute,
    "stress_autonomic": stress_autonomic.compute,
    "immune_inflammation": immune_inflammation.compute,
}

DOMAINS: list[str] = list(DOMAIN_REGISTRY)


def apply_safety(status: DomainStatus) -> DomainStatus:
    """Return a copy of ``status`` with all prose run through the safety filter.

    Sanitizes summary plus every list of generated strings. Any safety flags are
    appended to ``missing_data`` so they remain visible/auditable downstream.
    """
    flags: list[str] = []

    summary_res = safety.sanitize(status.summary)
    flags.extend(summary_res.flags)

    obs, f = safety.sanitize_list(status.observations); flags.extend(f)
    der, f = safety.sanitize_list(status.derived); flags.extend(f)
    inf, f = safety.sanitize_list(status.inferences); flags.extend(f)
    hyp, f = safety.sanitize_list(status.hypotheses); flags.extend(f)
    rec, f = safety.sanitize_list(status.recommendations); flags.extend(f)
    lev, f = safety.sanitize_list(status.levers); flags.extend(f)

    drivers = []
    for d in status.drivers:
        detail_res = safety.sanitize(d.detail)
        flags.extend(detail_res.flags)
        drivers.append(d.model_copy(update={"detail": detail_res.text}))

    evidence = []
    for ref in status.evidence:
        claim_res = safety.sanitize(ref.claim)
        flags.extend(claim_res.flags)
        evidence.append(ref.model_copy(update={"claim": claim_res.text}))

    missing = list(status.missing_data)
    if flags:
        missing.append(f"safety filter applied {len(flags)} adjustment(s) to generated text")

    return status.model_copy(
        update={
            "summary": summary_res.text,
            "observations": obs,
            "derived": der,
            "inferences": inf,
            "hypotheses": hyp,
            "recommendations": rec,
            "evidence": evidence,
            "missing_data": missing,
            "drivers": drivers,
            "levers": lev,
        }
    )


def run_one(ctx: DataContext, domain: str, persist: bool = False) -> DomainStatus:
    """Compute (and optionally persist) a single domain's status.

    Raises :class:`KeyError` if ``domain`` is not a canonical domain.
    """
    if domain not in DOMAIN_REGISTRY:
        raise KeyError(f"unknown domain: {domain!r}")
    raw = DOMAIN_REGISTRY[domain](ctx)
    raw = raw.model_copy(
        update={
            "drivers": levers_mod.build_drivers(raw.contributions),
            "levers": levers_mod.levers_for(domain),
        }
    )
    status = apply_safety(raw)
    if persist:
        persist_status(ctx, status)
    return status


def run_all(ctx: DataContext, persist: bool = False) -> list[DomainStatus]:
    """Compute (and optionally persist) all canonical domains."""
    results = [run_one(ctx, d, persist=False) for d in DOMAINS]
    if persist:
        for status in results:
            persist_status(ctx, status)
    return results


def persist_status(ctx: DataContext, status: DomainStatus) -> None:
    """Upsert a ``DomainStatus`` into the ``domain_status`` table.

    ``summary_json`` holds the full serialized DomainStatus; the scalar columns
    mirror key fields for cheap querying. Tolerates a missing table (no-op).
    """
    conn = ctx._conn  # interpretation owns interpretation tables
    try:
        conn.execute(
            """
            INSERT INTO domain_status
                (domain, as_of_ts, score, score_label, trend, confidence,
                 evidence_grade, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(domain, as_of_ts) DO UPDATE SET
                score=excluded.score, score_label=excluded.score_label,
                trend=excluded.trend, confidence=excluded.confidence,
                evidence_grade=excluded.evidence_grade,
                summary_json=excluded.summary_json
            """,
            (
                status.domain,
                status.as_of.isoformat(),
                status.score,
                status.score_label,
                status.trend.value,
                status.confidence.value,
                status.evidence_grade.value,
                status.model_dump_json(),
            ),
        )
        _audit(conn, "interpretation", f"computed domain_status for {status.domain}")
        conn.commit()
    except sqlite3.OperationalError:
        # domain_status table not present (e.g. partial schema); skip persistence.
        return


def load_cached(ctx: DataContext, domain: str) -> DomainStatus | None:
    """Return the most recent persisted ``DomainStatus`` for a domain, if any."""
    rows = ctx._query(
        "SELECT summary_json FROM domain_status WHERE domain=? ORDER BY as_of_ts DESC LIMIT 1",
        (domain,),
    )
    if not rows or not rows[0]["summary_json"]:
        return None
    return DomainStatus.model_validate(json.loads(rows[0]["summary_json"]))


def _audit(conn: sqlite3.Connection, event: str, detail: str) -> None:
    """Best-effort audit-log entry for a generated interpretation."""
    try:
        conn.execute(
            "INSERT INTO audit_log (ts, event, detail) VALUES (datetime('now'), ?, ?)",
            (event, detail),
        )
    except sqlite3.OperationalError:
        return
