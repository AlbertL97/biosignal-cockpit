"""Streaming parser for the whole-genome VCF (~1.1 GB, GRCh38, VCFv4.2).

The file is read line-by-line and never loaded into memory (ARCHITECTURE §4).
Only variants whose dbSNP ``rsID`` is in a target set are stored into
``genome_variants``. The target set = all rsIDs referenced by parsed Nebula
reports (``nebula_trait_variants``) plus a small curated, broadly-actionable
set defined here.

Public entry points: :func:`ingest_vcf`, :func:`lookup_genotype`.
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from app.config import VCF_FILE
from app.ingestion.nebula_reports import collect_nebula_rsids
from app.storage import db

logger = logging.getLogger(__name__)

# A small curated, well-known and broadly lifestyle/PGx-relevant set. These are
# deliberately conservative, widely-studied variants; interpretation is handled
# downstream with caution (ARCHITECTURE §8, task §4.4).
CURATED_RSIDS: set[str] = {
    "rs1801133",  # MTHFR C677T - folate metabolism
    "rs1801131",  # MTHFR A1298C
    "rs4988235",  # LCT - lactase persistence
    "rs762551",   # CYP1A2 - caffeine metabolism
    "rs1799853",  # CYP2C9*2 - drug metabolism
    "rs1057910",  # CYP2C9*3
    "rs4244285",  # CYP2C19*2
    "rs9939609",  # FTO - body mass / appetite
    "rs1815739",  # ACTN3 R577X - muscle fibre type
    "rs53576",    # OXTR
    "rs6265",     # BDNF Val66Met
    "rs429358",   # APOE
    "rs7412",     # APOE
    "rs1799945",  # HFE H63D - iron
    "rs1800562",  # HFE C282Y - hereditary haemochromatosis
    "rs12979860",  # IFNL3/IL28B
    "rs1695",     # GSTP1
    "rs671",      # ALDH2 - alcohol flush
    "rs73598374",  # ADA - sleep
    "rs1544410",  # VDR BsmI - vitamin D
}


def target_rsids(conn: sqlite3.Connection) -> set[str]:
    """Union of Nebula-referenced rsIDs and the curated actionable set."""
    return collect_nebula_rsids(conn) | {r.lower() for r in CURATED_RSIDS}


def _genotype_from_gt(gt: str, ref: str, alt: str) -> str | None:
    """Translate a VCF ``GT`` field (e.g. ``0/1``) into alleles (e.g. ``CT``).

    Handles phased (``|``) and unphased (``/``) separators and multi-allelic
    ALT lists. Returns ``None`` for missing genotypes.
    """
    sep = "|" if "|" in gt else "/"
    parts = gt.split(":")[0].split(sep)
    alleles = [ref] + alt.split(",")
    out: list[str] = []
    for p in parts:
        if p in (".", ""):
            return None
        try:
            idx = int(p)
        except ValueError:
            return None
        if 0 <= idx < len(alleles):
            out.append(alleles[idx])
        else:
            return None
    return "".join(out)


def iter_vcf_variants(
    vcf_path: str | Path,
    wanted: set[str],
) -> Iterator[dict[str, object]]:
    """Yield parsed variant dicts for rows whose rsID is in ``wanted``.

    Streams the file line-by-line. The ID column may contain multiple
    semicolon-separated IDs; the first matching ``rs*`` ID is used.

    Args:
        vcf_path: Path to the VCF file.
        wanted: Lower-cased rsIDs to keep.

    Yields:
        Dicts ready for insertion into ``genome_variants``.
    """
    if not wanted:
        return
    with open(vcf_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 10:
                continue
            ids = cols[2]
            if ids == "." or "rs" not in ids:
                continue
            rsid = None
            for token in ids.split(";"):
                if token.lower().startswith("rs") and token.lower() in wanted:
                    rsid = token.lower()
                    break
            if rsid is None:
                continue
            chrom, pos, _id, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
            sample = cols[9]
            genotype = _genotype_from_gt(sample, ref, alt)
            try:
                pos_int: int | None = int(pos)
            except ValueError:
                pos_int = None
            yield {
                "rsid": rsid,
                "chrom": chrom,
                "pos": pos_int,
                "ref": ref,
                "alt": alt,
                "genotype": genotype,
                "gene": None,
                "source": "vcf",
            }


def ingest_vcf(
    conn: sqlite3.Connection,
    vcf_path: str | Path | None = None,
    wanted: set[str] | None = None,
) -> dict[str, int]:
    """Stream the VCF and store only target-rsID variants.

    Args:
        conn: Open SQLite connection.
        vcf_path: Override path; defaults to :data:`app.config.VCF_FILE`.
        wanted: Override the target rsID set; defaults to :func:`target_rsids`.

    Returns:
        Counts keyed by ``variants`` and ``targeted`` (size of target set).
    """
    path = Path(vcf_path) if vcf_path is not None else VCF_FILE
    targets = wanted if wanted is not None else target_rsids(conn)
    counts = {"variants": 0, "targeted": len(targets)}
    if not path.exists():
        db.audit(conn, "ingest.vcf", f"missing file {path}")
        return counts

    buf: list[dict[str, object]] = []
    for variant in iter_vcf_variants(path, targets):
        buf.append(variant)
        if len(buf) >= 1000:
            counts["variants"] += db.bulk_insert(
                conn, "genome_variants", buf, or_replace=True
            )
            buf = []
            conn.commit()
    if buf:
        counts["variants"] += db.bulk_insert(
            conn, "genome_variants", buf, or_replace=True
        )
    conn.commit()
    db.audit(conn, "ingest.vcf", str(counts))
    conn.commit()
    return counts


def lookup_genotype(conn: sqlite3.Connection, rsid: str) -> str | None:
    """Return the stored genotype (e.g. ``"CT"``) for an rsID, or ``None``."""
    row = conn.execute(
        "SELECT genotype FROM genome_variants WHERE rsid = ?", (rsid.lower(),)
    ).fetchone()
    return row["genotype"] if row else None
