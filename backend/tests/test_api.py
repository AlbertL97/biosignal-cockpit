"""Tests for the API routers using an isolated temp DB and FastAPI TestClient."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.storage import db


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Build a TestClient backed by a freshly-seeded temp database.

    ``db.DB_PATH`` is patched so every router's ``db.connection()`` resolves to
    the temp file. The app is imported after patching.
    """
    test_db = tmp_path / "api.sqlite"
    monkeypatch.setattr(db, "DB_PATH", test_db, raising=False)
    db.init_db(test_db)

    conn = db.get_conn(test_db)
    # profile + a couple of measurements
    conn.executemany(
        "INSERT INTO profile (key, value) VALUES (?, ?)",
        [("dob", "1997-07-14"), ("biological_sex", "HKBiologicalSexMale")],
    )
    conn.executemany(
        "INSERT INTO measurements (metric, unit, value, start_ts) VALUES (?,?,?,?)",
        [
            ("heart_rate", "count/min", 60, "2024-01-01T08:00:00+00:00"),
            ("heart_rate", "count/min", 64, "2024-01-02T08:00:00+00:00"),
        ],
    )
    conn.execute(
        "INSERT INTO baselines (metric, mean, sd, n, window_days, computed_ts) "
        "VALUES (?,?,?,?,?,?)",
        ("heart_rate", 62.0, 2.0, 2, 90, "2024-01-02T00:00:00+00:00"),
    )
    cur = conn.execute(
        "INSERT INTO nebula_traits (trait, category, citation, percentile) "
        "VALUES (?,?,?,?)",
        ("Heart rate variability", "cardio", "Tegegne, 2023", 55.0),
    )
    tid = cur.lastrowid
    conn.execute(
        "INSERT INTO nebula_trait_variants "
        "(trait_id, rsid, genotype, gene, highlighted) VALUES (?,?,?,?,?)",
        (tid, "rs12345", "AG", "GENE1", 1),
    )
    conn.commit()
    conn.close()

    from app.main import app

    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_profile(client: TestClient) -> None:
    r = client.get("/api/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["dob"] == "1997-07-14"
    assert body["biological_sex"] == "HKBiologicalSexMale"
    assert body["coverage"]["heart_rate"] == 2


def test_metric_series(client: TestClient) -> None:
    r = client.get("/api/metrics/heart_rate")
    assert r.status_code == 200
    body = r.json()
    assert body["metric"] == "heart_rate"
    assert len(body["points"]) == 2
    assert body["baseline_mean"] == 62.0


def test_metric_not_found(client: TestClient) -> None:
    r = client.get("/api/metrics/does_not_exist")
    assert r.status_code == 404


def test_genome_traits_list(client: TestClient) -> None:
    r = client.get("/api/genome/traits")
    assert r.status_code == 200
    traits = r.json()
    assert len(traits) == 1
    assert traits[0]["trait"] == "Heart rate variability"


def test_genome_trait_detail(client: TestClient) -> None:
    listing = client.get("/api/genome/traits").json()
    tid = listing[0]["id"]
    r = client.get(f"/api/genome/traits/{tid}")
    assert r.status_code == 200
    detail = r.json()
    assert len(detail["variants"]) == 1
    assert detail["variants"][0]["rsid"] == "rs12345"
    assert detail["variants"][0]["highlighted"] is True


def test_genome_trait_404(client: TestClient) -> None:
    r = client.get("/api/genome/traits/99999")
    assert r.status_code == 404


def test_genome_category_filter(client: TestClient) -> None:
    r = client.get("/api/genome/traits", params={"category": "cardio"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    r2 = client.get("/api/genome/traits", params={"category": "nope"})
    assert r2.json() == []
