"""Score explanations: what is raising/lowering a domain, and research-informed
levers that may improve it.

``drivers`` are derived directly from each domain's own ``contributions`` (so they
reflect the real data). ``levers`` are a curated, evidence-informed, deliberately
non-clinical knowledge base of general lifestyle actions associated with the
domain in the literature. Wording stays cautious (this is a self-experiment, not
medical advice).
"""
from __future__ import annotations

from app.models.contracts import Contribution, Driver

# Human-readable names for metric keys that may appear in contributions.
_HUMAN: dict[str, str] = {
    "resting_heart_rate": "resting heart rate",
    "RestingHeartRate": "resting heart rate",
    "hrv_sdnn": "heart-rate variability (HRV)",
    "HeartRateVariabilitySDNN": "heart-rate variability (HRV)",
    "heart_rate": "heart rate",
    "walking_heart_rate_avg": "walking heart rate",
    "oxygen_saturation": "blood-oxygen saturation",
    "vo2max": "estimated VO₂max",
    "step_count": "daily steps",
    "StepCount": "daily steps",
    "active_energy": "active energy burned",
    "exercise_time": "exercise minutes",
    "flights_climbed": "flights climbed",
    "walking_speed": "walking speed",
    "walking_asymmetry_pct": "walking asymmetry",
    "distance_walking_running": "walking/running distance",
    "sleep_hours": "sleep duration",
    "sleep_regularity": "sleep regularity",
    "rem_fraction": "REM-sleep fraction",
    "workout_load": "training load",
    "workout_count": "workout frequency",
    "fiber": "dietary fiber",
    "DietaryFiber": "dietary fiber",
    "sugar": "added/total sugar",
    "DietarySugar": "sugar intake",
    "protein": "protein intake",
    "energy": "calorie intake",
    "water": "hydration",
    "sodium": "sodium intake",
    "time_in_daylight": "daylight exposure",
}


def humanize(metric: str) -> str:
    """Return a readable label for a metric key."""
    if metric.startswith("trait:"):
        return metric.split(":", 1)[1].strip()
    if metric in _HUMAN:
        return _HUMAN[metric]
    if "_" in metric:
        return metric.replace("_", " ")
    # split CamelCase HK identifiers, e.g. WalkingAsymmetryPercentage
    out = "".join(f" {c.lower()}" if c.isupper() else c for c in metric).strip()
    return out or metric


def build_drivers(contributions: list[Contribution], limit: int = 6) -> list[Driver]:
    """Turn raw contributions into readable 'what's shaping this score' drivers."""
    ranked = sorted(contributions, key=lambda c: c.weight, reverse=True)
    drivers: list[Driver] = []
    for c in ranked:
        if c.direction == "supportive":
            direction = "raising"
            verb = "is supporting"
        elif c.direction == "adverse":
            direction = "lowering"
            verb = "is weighing on"
        else:
            direction = "neutral"
            verb = "is a mixed/uncertain factor for"
        name = humanize(c.metric)
        src = c.source.replace("_", " ")
        val = "" if c.value is None else f" (latest: {c.value})"
        gene = " genetic context" if c.source in {"genome", "nebula"} else ""
        drivers.append(
            Driver(
                factor=f"{name}{gene}".strip(),
                direction=direction,
                detail=f"{name}{val} from {src} {verb} this score.",
            )
        )
        if len(drivers) >= limit:
            break
    return drivers


# Evidence-informed, non-clinical levers per domain. General lifestyle actions
# associated with the domain in the literature — not personalised medical advice.
LEVERS: dict[str, list[str]] = {
    "gut": [
        "Raise dietary fiber toward ~30 g/day — fermentable fiber is the main prebiotic substrate for short-chain-fatty-acid–producing bacteria.",
        "Add fermented foods / probiotics (yogurt, kefir, sauerkraut, kimchi), which are associated with greater microbiome diversity.",
        "Eat a wider variety of plants per week (the '30 plants' heuristic) — plant diversity tracks with microbial diversity.",
        "Keep up regular aerobic activity, which is independently associated with higher gut-microbial diversity.",
        "Reduce ultra-processed foods, added sugar, and alcohol; protect sleep and manage stress (gut–brain axis).",
    ],
    "brain": [
        "Prioritise 7–9 h of regular sleep — slow-wave and REM sleep support memory consolidation and glymphatic clearance.",
        "Sustain regular aerobic exercise, associated with higher BDNF and better executive function.",
        "Favour a Mediterranean-style dietary pattern (omega-3s, polyphenols); limit alcohol.",
        "Manage chronic stress (HRV-guided breathing, mindfulness) to protect cognitive readiness.",
        "Get morning daylight to anchor circadian rhythm and daytime alertness.",
    ],
    "cardiovascular": [
        "Accumulate ≥150 min/week of moderate (or 75 min vigorous) aerobic activity to support VO₂max and resting heart rate.",
        "Add 2× weekly zone-2 sessions — improves HRV and autonomic balance over time.",
        "Protect sleep and limit alcohol; both acutely depress HRV and raise resting heart rate.",
        "Keep dietary sodium moderate and fiber high; favour unsaturated over saturated fats.",
        "Track resting HR / HRV trends against your own baseline rather than population norms.",
    ],
    "oral_dental": [
        "Reduce frequency (not just amount) of sugar and acidic-drink exposures — frequency drives demineralisation.",
        "Avoid grazing; cluster carbohydrate intake into meals to give enamel remineralisation time.",
        "Maintain hydration and saliva flow; stay current with brushing/flossing and dental check-ups.",
        "Limit alcohol and smoking, both linked to periodontal disease risk.",
    ],
    "musculoskeletal": [
        "Do progressive resistance training 2–3×/week — the strongest lever against age- and genetics-related muscle loss.",
        "Hit ~1.6 g/kg/day protein, distributed across meals, to maximise muscle-protein synthesis.",
        "Ensure recovery: adequate sleep and deloads when training load and HRV diverge.",
        "Keep daily steps up to preserve mobility metrics (gait speed, asymmetry).",
        "Ensure adequate calories and vitamin D / calcium for bone and muscle maintenance.",
    ],
    "metabolic": [
        "Align energy intake with activity; sustained surplus or deficit both stress metabolic markers.",
        "Prioritise protein and fiber, reduce refined carbohydrate and added sugar for steadier glucose.",
        "Add post-meal walks and regular aerobic + resistance training to improve insulin sensitivity.",
        "Protect sleep — short/irregular sleep worsens glucose handling and appetite regulation.",
    ],
    "sleep_recovery": [
        "Keep a consistent sleep/wake schedule (including weekends) — regularity predicts outcomes as much as duration.",
        "Get bright light in the morning and dim light at night to strengthen circadian signalling.",
        "Avoid caffeine within ~8–10 h and alcohol within ~3–4 h of bed; both fragment sleep and lower HRV.",
        "Keep the room cool and dark; finish intense exercise a few hours before bed.",
        "Use HRV and resting-heart-rate trends as recovery signals to guide training.",
    ],
    "stress_autonomic": [
        "Practise slow breathing (~6 breaths/min) or HRV-biofeedback to raise vagal tone.",
        "Protect sleep and recovery — sleep debt is a primary driver of low HRV.",
        "Moderate alcohol and late caffeine, which blunt overnight parasympathetic recovery.",
        "Balance training stress with easy days; spend more time in low-intensity zones.",
        "Add daylight, nature exposure, and mindfulness, associated with autonomic balance.",
    ],
    "immune_inflammation": [
        "Prioritise sleep — short sleep is associated with higher inflammatory markers and infection risk.",
        "Stay physically active at moderate volumes; avoid chronic over-reaching.",
        "Eat a fiber-rich, polyphenol-rich, omega-3–containing diet; limit ultra-processed foods and alcohol.",
        "Manage chronic stress (HRV-guided practices) — sustained stress is pro-inflammatory.",
        "Note: inflammation cannot be confirmed without lab markers (e.g. CRP) — these are lifestyle proxies only.",
    ],
}


def levers_for(domain: str) -> list[str]:
    """Return the curated improvement levers for a domain (empty if unknown)."""
    return list(LEVERS.get(domain, []))
