"""Parser for Nebula Genomics trait reports (``DNA_reports/*.pdf``).

Each PDF describes one trait. We extract:

* trait name and citation (from the filename and/or first-page heading),
* a category tag and percentile / score / score label where present,
* the per-variant table: rsID, genotype, gene, effect size, frequency,
  p-value, and whether the row is highlighted (the user's genotype).

Layouts vary between reports, so extraction is best-effort and regex-driven:
unparseable rows are skipped and logged rather than aborting the file
(ARCHITECTURE §4). Results populate ``nebula_traits`` and
``nebula_trait_variants``.

Public entry point: :func:`ingest_nebula_reports`.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber

from app.config import NEBULA_REPORTS_DIR
from app.storage import db

logger = logging.getLogger(__name__)

# Filename like: "Heart rate variability (Tegegne, 2023).pdf"
_FILENAME_RE = re.compile(r"^(?P<trait>.+?)\s*\((?P<citation>[^)]+)\)\s*$")

_RSID_RE = re.compile(r"\brs\d{2,}\b", re.IGNORECASE)
_GENOTYPE_RE = re.compile(r"\b([ACGT])[/|]?([ACGT])\b")
_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9-]{1,14})\b")
_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_PERCENTILE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:th|st|nd|rd)?\s*percentile", re.I)
_CATEGORY_RE = re.compile(r"Category\s*[:\-]?\s*(.+)", re.I)


@dataclass
class TraitRecord:
    """Parsed contents of a single Nebula report PDF."""

    trait: str
    citation: str | None = None
    category: str | None = None
    percentile: float | None = None
    score: float | None = None
    score_label: str | None = None
    pdf_path: str = ""
    variants: list[dict[str, Any]] = field(default_factory=list)


def _parse_filename(path: Path) -> tuple[str, str | None]:
    """Return ``(trait, citation)`` derived from the PDF filename."""
    stem = path.stem.strip()
    m = _FILENAME_RE.match(stem)
    if m:
        return m.group("trait").strip(), m.group("citation").strip()
    return stem, None


def _safe_float(token: str | None) -> float | None:
    """Convert a token to float, tolerating ``e``-notation and stray spaces."""
    if not token:
        return None
    token = token.replace(" ", "")
    try:
        return float(token)
    except ValueError:
        m = _FLOAT_RE.search(token)
        return float(m.group()) if m else None


def _extract_genotype(cells: list[str]) -> str | None:
    """Find a 2-letter genotype like ``A/G`` / ``AG`` in a row's cells."""
    for c in cells:
        m = _GENOTYPE_RE.search(c.strip())
        if m and len(c.strip()) <= 4:
            return f"{m.group(1)}{m.group(2)}"
    return None


def _parse_variant_row(cells: list[str]) -> dict[str, Any] | None:
    """Best-effort parse of one variant-table row into a column dict.

    A row must contain an rsID to be considered a variant row. Effect size,
    frequency, p-value and gene are extracted opportunistically; missing ones
    become ``None``.
    """
    joined = " ".join(c for c in cells if c)
    rs = _RSID_RE.search(joined)
    if not rs:
        return None
    rsid = rs.group().lower()

    gene = None
    for c in cells:
        token = c.strip()
        if token and token.isupper() and not token.startswith("RS") and _GENE_RE.fullmatch(token):
            gene = token
            break

    floats: list[float] = []
    p_value: float | None = None
    for c in cells:
        if _RSID_RE.search(c):
            continue
        pv = re.search(r"\d+(?:\.\d+)?\s*[eE]\s*[-+]?\d+", c)
        if pv and p_value is None:
            p_value = _safe_float(pv.group())
            continue
        f = _safe_float(c) if _FLOAT_RE.fullmatch(c.strip()) else None
        if f is not None:
            floats.append(f)

    effect_size = floats[0] if floats else None
    frequency = next((f for f in floats[1:] if 0.0 <= f <= 1.0), None)

    return {
        "rsid": rsid,
        "genotype": _extract_genotype(cells),
        "gene": gene,
        "effect_size": effect_size,
        "frequency": frequency,
        "p_value": p_value,
        "highlighted": 0,
    }


def parse_report(path: str | Path) -> TraitRecord:
    """Parse a single Nebula report PDF into a :class:`TraitRecord`.

    Never raises on malformed content: failures degrade to whatever could be
    extracted (at minimum the trait name from the filename).

    Args:
        path: Path to a Nebula report PDF.

    Returns:
        A :class:`TraitRecord` with as many fields populated as possible.
    """
    p = Path(path)
    trait, citation = _parse_filename(p)
    rec = TraitRecord(trait=trait, citation=citation, pdf_path=str(p))

    try:
        with pdfplumber.open(str(p)) as pdf:
            full_text_parts: list[str] = []
            seen_rsids: set[str] = set()
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text_parts.append(text)
                # Structured tables first.
                for table in page.extract_tables() or []:
                    for raw_row in table:
                        cells = [(c or "").strip() for c in raw_row]
                        variant = _parse_variant_row(cells)
                        if variant and variant["rsid"] not in seen_rsids:
                            seen_rsids.add(variant["rsid"])
                            rec.variants.append(variant)
            full_text = "\n".join(full_text_parts)

            # Fallback: scan text lines for rsIDs not found via tables.
            for line in full_text.splitlines():
                if _RSID_RE.search(line):
                    cells = re.split(r"\s{1,}|\t", line.strip())
                    variant = _parse_variant_row(cells)
                    if variant and variant["rsid"] not in seen_rsids:
                        seen_rsids.add(variant["rsid"])
                        rec.variants.append(variant)

            _enrich_from_text(rec, full_text)
    except Exception as exc:  # pragma: no cover - corrupt/locked PDF
        logger.warning("Failed to parse %s: %s", p.name, exc)

    return rec


def _enrich_from_text(rec: TraitRecord, text: str) -> None:
    """Pull percentile / score / category hints from free text."""
    m = _PERCENTILE_RE.search(text)
    if m:
        rec.percentile = _safe_float(m.group(1))
    cm = _CATEGORY_RE.search(text)
    if cm:
        rec.category = cm.group(1).strip().splitlines()[0][:80]
    sm = re.search(r"(?:score|result)\s*[:\-]?\s*([A-Za-z ]{3,30})", text, re.I)
    if sm:
        rec.score_label = sm.group(1).strip()


def ingest_nebula_reports(
    conn: sqlite3.Connection,
    reports_dir: str | Path | None = None,
) -> dict[str, int]:
    """Parse every PDF in ``reports_dir`` and store traits + variants.

    Args:
        conn: Open SQLite connection (caller owns the outer transaction).
        reports_dir: Override directory; defaults to
            :data:`app.config.NEBULA_REPORTS_DIR`.

    Returns:
        Counts keyed by ``traits``, ``variants``, ``failed``.
    """
    directory = Path(reports_dir) if reports_dir is not None else NEBULA_REPORTS_DIR
    counts = {"traits": 0, "variants": 0, "failed": 0}
    if not directory.exists():
        db.audit(conn, "ingest.nebula", f"missing dir {directory}")
        return counts

    for pdf_path in sorted(directory.glob("*.pdf")):
        try:
            rec = parse_report(pdf_path)
        except Exception as exc:  # pragma: no cover
            logger.warning("Skipping %s: %s", pdf_path.name, exc)
            counts["failed"] += 1
            continue

        cur = conn.execute(
            "INSERT INTO nebula_traits "
            "(trait, category, citation, percentile, score, score_label, pdf_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                rec.trait,
                rec.category,
                rec.citation,
                rec.percentile,
                rec.score,
                rec.score_label,
                rec.pdf_path,
            ),
        )
        trait_id = cur.lastrowid
        counts["traits"] += 1

        if rec.variants:
            rows = [
                {
                    "trait_id": trait_id,
                    "rsid": v["rsid"],
                    "genotype": v.get("genotype"),
                    "gene": v.get("gene"),
                    "effect_size": v.get("effect_size"),
                    "frequency": v.get("frequency"),
                    "p_value": v.get("p_value"),
                    "highlighted": v.get("highlighted", 0),
                }
                for v in rec.variants
            ]
            counts["variants"] += db.bulk_insert(conn, "nebula_trait_variants", rows)

    conn.commit()
    db.audit(conn, "ingest.nebula", str(counts))
    conn.commit()
    return counts


def collect_nebula_rsids(conn: sqlite3.Connection) -> set[str]:
    """Return all rsIDs referenced by parsed Nebula reports (for the VCF filter)."""
    rows = conn.execute(
        "SELECT DISTINCT rsid FROM nebula_trait_variants WHERE rsid IS NOT NULL"
    ).fetchall()
    return {r["rsid"].lower() for r in rows if r["rsid"]}
