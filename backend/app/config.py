"""Central configuration. All data paths resolve to the project root.

Real data files are git-ignored and live at the repo root. Override any path via
environment variables (see ``.env.example``).
"""
from __future__ import annotations

import os
from pathlib import Path

# backend/app/config.py -> project root is two levels up from backend/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("HA_DATA_ROOT", PROJECT_ROOT))

# --- Source data files (git-ignored) ---
APPLE_HEALTH_XML = DATA_ROOT / "eksport.xml"
APPLE_HEALTH_CDA = DATA_ROOT / "export_cda.xml"
VCF_FILE = DATA_ROOT / "NG1E19KTCQ.mm2.sortdup.bqsr.hc (1).vcf"
NEBULA_REPORTS_DIR = DATA_ROOT / "DNA_reports"
GPX_DIR = DATA_ROOT / "workout-routes"
# CRAM intentionally ignored (66 GB raw alignments, not needed).

# --- Generated artifacts (git-ignored) ---
DB_PATH = Path(os.environ.get("HA_DB_PATH", DATA_ROOT / "data" / "health.sqlite"))

# --- Evidence / PubMed ---
ENTREZ_EMAIL = os.environ.get("ENTREZ_EMAIL", "")        # required by NCBI E-utilities
ENTREZ_API_KEY = os.environ.get("ENTREZ_API_KEY", "")    # optional, raises rate limit
PUBMED_CACHE = Path(os.environ.get("HA_PUBMED_CACHE", DATA_ROOT / "data" / "evidence"))

# --- API ---
API_HOST = os.environ.get("HA_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("HA_API_PORT", "8000"))
CORS_ORIGINS = os.environ.get("HA_CORS_ORIGINS", "http://localhost:5173").split(",")
