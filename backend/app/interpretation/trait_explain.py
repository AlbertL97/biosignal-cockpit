"""Plain-language explanations for polygenic trait reports.

`describe_trait` says what a trait *is*; `interpret_percentile` says what the
user's percentile *means* — always framed as a non-deterministic genetic
predisposition, never a diagnosis.
"""
from __future__ import annotations

# Curated one-liners for common trait keywords. Generic fallback otherwise.
TRAIT_DESCRIPTIONS: dict[str, str] = {
    "carbohydrate consumption": "A behavioural trait: the genetic tendency to eat more or fewer carbohydrates. It reflects appetite/preference biology, not a dietary requirement.",
    "coffee consumption": "Genetic tendency toward higher or lower coffee/caffeine intake, largely via caffeine-metabolism genes.",
    "bitter taste perception": "How strongly you perceive bitter compounds (e.g. PROP/PTC), driven mainly by TAS2R taste-receptor variants.",
    "eye color": "Genetic prediction of iris pigmentation, dominated by a few well-understood pigmentation genes.",
    "25-hydroxyvitamin d": "Genetic influence on circulating vitamin D level — a predisposition, strongly modified by sun exposure and diet.",
    "vitamin d level": "Genetic influence on circulating vitamin D level — a predisposition, strongly modified by sun exposure and diet.",
    "bone mineral density": "Genetic contribution to bone density, a factor in long-term skeletal strength (heavily modified by exercise and nutrition).",
    "height": "One of the most polygenic human traits — thousands of variants each nudge adult height up or down.",
    "short stature": "Genetic contribution to being shorter than average; highly polygenic and strongly environment-modified.",
    "male-pattern baldness": "Genetic predisposition to androgenic hair loss; cosmetic, not a health risk.",
    "sleep duration": "Genetic tendency toward shorter or longer habitual sleep, one input among many to actual sleep.",
    "daytime napping": "Genetic tendency toward daytime napping / sleep pressure.",
    "snoring": "Genetic predisposition to snoring (airway/anatomy related).",
    "walking pace": "Genetic tendency toward a faster or slower self-reported walking pace, a rough fitness proxy.",
    "reaction time": "Genetic contribution to simple reaction speed, a basic processing-speed measure.",
    "handed": "Genetic contribution to hand preference (left/right/mixed).",
    "ambidext": "Genetic contribution to mixed-handedness.",
    "beat synchron": "Genetic tendency to synchronise movement to a musical beat — a rhythm/musicality trait.",
    "skin pigmentation": "Genetic prediction of skin pigmentation/tanning response.",
    "skin aging": "Genetic contribution to visible skin ageing (e.g. wrinkling), cosmetic.",
    "wrinkl": "Genetic contribution to wrinkle formation, cosmetic.",
    "dental development": "Genetic influence on tooth development/timing.",
    "birth weight": "Genetic contribution to your own birth weight (a developmental trait).",
    "familial short stature": "Genetic contribution to familial (inherited) short stature.",
}

GENERIC_DESCRIPTION = (
    "A polygenic trait: your score is the combined effect of many common DNA "
    "variants, each with a tiny influence. It describes a population-level "
    "genetic tendency, not your actual measured value."
)


def describe_trait(trait: str) -> str:
    ln = (trait or "").lower()
    for kw, desc in TRAIT_DESCRIPTIONS.items():
        if kw in ln:
            return desc
    return GENERIC_DESCRIPTION


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def interpret_percentile(
    trait: str, percentile: float | None, score_label: str | None
) -> str:
    """Explain what the user's percentile means, with the standard caveats."""
    caveat = (
        " This is a genetic predisposition only — it is not a diagnosis or a "
        "measurement, and lifestyle and environment usually matter at least as "
        "much. Most trait–variant links are still incompletely understood."
    )
    if percentile is None:
        base = (
            f"No percentile was reported for {trait}. The variant table below "
            "still shows which of the study's variants you carry."
        )
        return base + caveat

    p = int(round(percentile))
    higher_than = max(0, min(100, p))
    label = f" — reported as a {score_label.strip()} genetic score" if score_label else ""
    where = (
        "around the middle of the population"
        if 25 <= p <= 75
        else "toward the lower end" if p < 25 else "toward the higher end"
    )
    return (
        f"Your polygenic score for {trait} sits in the {_ordinal(p)} percentile{label}: "
        f"genetically higher than about {higher_than}% of people, i.e. {where}. "
        "A high or low percentile here is common and expected for at least some "
        "traits." + caveat
    )
