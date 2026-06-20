"""Current headline metrics with real values (resting HR, HRV, steps, etc.).

Replaces the misleading raw record-count "coverage" with meaningful numbers
computed over each signal's own recent window via the DataContext.
"""
from __future__ import annotations

from statistics import mean

from app.interpretation.context import DataContext
from app.models.contracts import Highlight


def compute_highlights(ctx: DataContext) -> list[Highlight]:
    """Build the dashboard's headline metrics from whatever data exists."""
    out: list[Highlight] = []

    def add(label: str, val: float | None, unit: str, ndigits: int = 0,
            detail: str | None = None) -> None:
        if val is None:
            return
        num = round(val, ndigits)
        if ndigits == 0:
            num = int(num)
        out.append(Highlight(label=label, value=f"{num:,} {unit}".strip(), detail=detail))

    add("Resting HR", ctx.mean_value("RestingHeartRate", days=30), "bpm",
        detail="30-day average")
    add("HRV (SDNN)", ctx.mean_value("HeartRateVariabilitySDNN", days=30), "ms",
        detail="30-day average")
    add("Steps", ctx.mean_value("StepCount", days=30), "/day", detail="30-day average")
    add("Active energy", ctx.mean_value("ActiveEnergyBurned", days=30), "kcal/day",
        detail="30-day average")

    sleep = ctx.sleep_hours_recent(30)
    if sleep:
        add("Sleep", mean(sleep), "h/night", ndigits=1, detail="recent average")

    add("VO₂max", ctx.latest_value("VO2Max"), "mL/kg/min", ndigits=1,
        detail="latest estimate")
    add("Blood oxygen", ctx.mean_value("OxygenSaturation", days=30), "%", ndigits=1,
        detail="30-day average")

    cal = ctx.nutrition_mean("DietaryEnergyConsumed", days=30)
    add("Calories", cal, "kcal/day", detail="logged, 30-day average")
    return out
