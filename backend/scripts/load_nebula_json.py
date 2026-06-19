"""Load vision-extracted Nebula JSON batches into the DB.

Reads data/nebula_extracted/batch_*.json (each a JSON list of trait objects with
this shape)::

    {
      "pdf": "Heart rate variability (Tegegne, 2023).pdf",
      "trait": "Heart rate variability",
      "category": "Heart",
      "percentile": 3,
      "score": -0.72,
      "score_label": "very low",
      "variants": [
        {"rsid":"rs2013349","genotype":"T/A","gene":"NDUFA11",
         "effect_size":-0.09,"frequency":0.08,"p_value":3.9e-42,"highlighted":false}
      ]
    }

Replaces the filename-only rows from the PDF parser with the real extracted data.
Run from backend/:  python -m scripts.load_nebula_json
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

from app.config import DATA_ROOT
from app.storage import db

EXTRACT_DIR = DATA_ROOT / "data" / "nebula_extracted"


def load() -> dict[str, int]:
    files = sorted(glob.glob(str(EXTRACT_DIR / "batch_*.json")))
    if not files:
        raise SystemExit(f"No batch_*.json in {EXTRACT_DIR}")

    traits: list[dict] = []
    for f in files:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        traits.extend(data)

    with db.connection() as conn:
        conn.execute("DELETE FROM nebula_trait_variants")
        conn.execute("DELETE FROM nebula_traits")
        n_traits = n_vars = 0
        for t in traits:
            cur = conn.execute(
                "INSERT INTO nebula_traits(trait,category,citation,percentile,score,score_label,pdf_path)"
                " VALUES(?,?,?,?,?,?,?)",
                (
                    t.get("trait"),
                    t.get("category"),
                    t.get("citation") or t.get("pdf"),
                    t.get("percentile"),
                    t.get("score"),
                    t.get("score_label"),
                    t.get("pdf"),
                ),
            )
            tid = cur.lastrowid
            n_traits += 1
            for v in t.get("variants") or []:
                conn.execute(
                    "INSERT INTO nebula_trait_variants"
                    "(trait_id,rsid,genotype,gene,effect_size,frequency,p_value,highlighted)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (
                        tid,
                        v.get("rsid"),
                        v.get("genotype"),
                        v.get("gene"),
                        v.get("effect_size"),
                        v.get("frequency"),
                        v.get("p_value"),
                        1 if v.get("highlighted") else 0,
                    ),
                )
                n_vars += 1
        db.audit(conn, "load_nebula_json", f"traits={n_traits} variants={n_vars}")
    return {"traits": n_traits, "variants": n_vars}


if __name__ == "__main__":
    print(load())
