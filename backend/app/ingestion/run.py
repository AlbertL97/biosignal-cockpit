"""Ingestion pipeline CLI.

Run with ``python -m app.ingestion.run`` from ``backend/``.

Order matters: Nebula reports are parsed before the VCF because the VCF target
rsID set is derived from the Nebula variant table (ARCHITECTURE §4). Every stage
writes a summary to ``audit_log``.

Use ``--reset`` to rebuild the database from scratch, and ``--skip`` to omit
specific stages (e.g. ``--skip vcf`` while iterating).
"""
from __future__ import annotations

import argparse
import logging
import time

from app.config import DB_PATH
from app.ingestion import apple_health, gpx, nebula_reports, vcf
from app.storage import db

logger = logging.getLogger("ingestion")

# Order: nebula must precede vcf.
STAGES = ("apple_health", "nebula", "vcf", "gpx")


def run_pipeline(
    *,
    reset: bool = False,
    skip: set[str] | None = None,
) -> dict[str, dict[str, int]]:
    """Initialise the DB and run all ingestion stages in order.

    Args:
        reset: Drop and recreate the database before ingesting.
        skip: Stage names to skip (subset of :data:`STAGES`).

    Returns:
        Mapping of stage name -> per-stage counts.
    """
    skip = skip or set()
    if reset:
        db.reset_db()
    else:
        db.init_db()

    results: dict[str, dict[str, int]] = {}
    conn = db.get_conn()
    db.audit(conn, "pipeline.start", f"reset={reset} skip={sorted(skip)}")
    conn.commit()
    try:
        if "apple_health" not in skip:
            t = time.time()
            results["apple_health"] = apple_health.ingest_apple_health(conn)
            logger.info("apple_health done in %.1fs: %s", time.time() - t,
                        results["apple_health"])
        if "nebula" not in skip:
            t = time.time()
            results["nebula"] = nebula_reports.ingest_nebula_reports(conn)
            logger.info("nebula done in %.1fs: %s", time.time() - t, results["nebula"])
        if "vcf" not in skip:
            t = time.time()
            results["vcf"] = vcf.ingest_vcf(conn)
            logger.info("vcf done in %.1fs: %s", time.time() - t, results["vcf"])
        if "gpx" not in skip:
            t = time.time()
            results["gpx"] = gpx.ingest_gpx(conn)
            logger.info("gpx done in %.1fs: %s", time.time() - t, results["gpx"])
        db.audit(conn, "pipeline.done", str(results))
        conn.commit()
    finally:
        conn.close()
    return results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the health-data ingestion pipeline.")
    parser.add_argument("--reset", action="store_true", help="rebuild the DB first")
    parser.add_argument(
        "--skip", nargs="*", default=[], choices=STAGES, help="stages to skip"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("DB: %s", DB_PATH)
    results = run_pipeline(reset=args.reset, skip=set(args.skip))
    logger.info("Pipeline complete: %s", results)


if __name__ == "__main__":
    main()
