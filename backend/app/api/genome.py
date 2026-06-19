"""``/api/genome/traits`` and ``/api/genome/traits/{id}`` — Nebula traits."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.contracts import NebulaTrait, TraitVariant
from app.storage import db

router = APIRouter(prefix="/api/genome", tags=["genome"])


@router.get("/traits", response_model=list[NebulaTrait])
def list_traits(
    category: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[NebulaTrait]:
    """List parsed Nebula traits (without variant tables for brevity).

    Args:
        category: Optional case-insensitive category filter.
        limit: Maximum number of traits returned.
    """
    sql = "SELECT * FROM nebula_traits"
    params: list[object] = []
    if category:
        sql += " WHERE category LIKE ?"
        params.append(f"%{category}%")
    sql += " ORDER BY trait LIMIT ?"
    params.append(limit)

    with db.connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        NebulaTrait(
            id=r["id"],
            trait=r["trait"],
            category=r["category"],
            citation=r["citation"],
            percentile=r["percentile"],
            score=r["score"],
            score_label=r["score_label"],
            variants=[],
        )
        for r in rows
    ]


@router.get("/traits/{trait_id}", response_model=NebulaTrait)
def get_trait(trait_id: int) -> NebulaTrait:
    """Return a single trait plus its variant table.

    Raises:
        HTTPException: 404 if the trait id does not exist.
    """
    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM nebula_traits WHERE id = ?", (trait_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Trait {trait_id} not found")
        var_rows = conn.execute(
            "SELECT * FROM nebula_trait_variants WHERE trait_id = ?", (trait_id,)
        ).fetchall()

    variants = [
        TraitVariant(
            rsid=v["rsid"],
            genotype=v["genotype"],
            gene=v["gene"],
            effect_size=v["effect_size"],
            frequency=v["frequency"],
            p_value=v["p_value"],
            highlighted=bool(v["highlighted"]),
        )
        for v in var_rows
        if v["rsid"]
    ]
    return NebulaTrait(
        id=row["id"],
        trait=row["trait"],
        category=row["category"],
        citation=row["citation"],
        percentile=row["percentile"],
        score=row["score"],
        score_label=row["score_label"],
        variants=variants,
    )
