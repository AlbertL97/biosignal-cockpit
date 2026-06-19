"""Safety filter for non-diagnostic, cautious medical language.

Per task §8 / §14 and ARCHITECTURE.md §8, generated prose must never diagnose,
prove, or imply deterministic genomic destiny. This module scans every piece of
text the engine emits and rewrites banned phrasings into cautious equivalents,
flagging anything it cannot safely soften.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Each rule is (compiled pattern, cautious replacement). Patterns are
# case-insensitive and intentionally narrow to avoid mangling benign text.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\byou have\b", re.I), "the pattern may be consistent with"),
    (re.compile(r"\bthis proves\b", re.I), "this is a non-diagnostic proxy that may suggest"),
    (re.compile(r"\bproves that\b", re.I), "may be consistent with"),
    (re.compile(r"\byour ([a-z/ ]+?) is unhealthy\b", re.I),
     r"signals related to your \1 may warrant cautious attention"),
    (re.compile(r"\byour ([a-z/ ]+?) is healthy\b", re.I),
     r"signals related to your \1 currently appear supportive"),
    (re.compile(r"\byour genome means\b", re.I),
     "your genomic context offers non-deterministic, probabilistic signals that"),
    (re.compile(r"\byour genes? means?\b", re.I),
     "your genomic context probabilistically suggests"),
    (re.compile(r"\bthis diagnosis\b", re.I), "this non-diagnostic pattern"),
    (re.compile(r"\bdiagnos(e|es|ed|is)\b", re.I), "non-diagnostic assessment"),
    (re.compile(r"\bthis supplement will fix\b", re.I),
     "evidence does not support that any supplement will fix"),
    (re.compile(r"\bwill fix\b", re.I), "may, with professional guidance, help support"),
    (re.compile(r"\bwill cure\b", re.I), "is not a cure for"),
    (re.compile(r"\byou are at risk of\b", re.I), "data may be consistent with a possible context for"),
    (re.compile(r"\bguarantee(s|d)?\b", re.I), "may be associated with"),
    (re.compile(r"\bdefinitely\b", re.I), "possibly"),
    (re.compile(r"\bcertainly\b", re.I), "possibly"),
]

# Phrases we cannot safely auto-rewrite; their presence raises a flag.
_HARD_BLOCK: list[re.Pattern[str]] = [
    re.compile(r"\bcancer\b", re.I),
    re.compile(r"\btumou?r\b", re.I),
]


@dataclass
class SafetyResult:
    """Outcome of running text through the safety filter."""

    text: str
    changed: bool = False
    flags: list[str] = field(default_factory=list)


def sanitize(text: str) -> SafetyResult:
    """Rewrite banned diagnostic phrasing in ``text`` and flag hard blocks.

    Returns a :class:`SafetyResult` with the (possibly rewritten) text, whether
    any change occurred, and human-readable flags for unrewritable matches.
    """
    if not text:
        return SafetyResult(text=text)
    out = text
    changed = False
    flags: list[str] = []
    for pattern, replacement in _RULES:
        new = pattern.sub(replacement, out)
        if new != out:
            changed = True
            flags.append(f"rewrote banned phrasing: /{pattern.pattern}/")
            out = new
    for pattern in _HARD_BLOCK:
        if pattern.search(out):
            flags.append(f"flagged sensitive term requiring clinical context: /{pattern.pattern}/")
    return SafetyResult(text=out, changed=changed, flags=flags)


def sanitize_list(items: list[str]) -> tuple[list[str], list[str]]:
    """Sanitize a list of strings; return ``(clean_items, all_flags)``."""
    clean: list[str] = []
    flags: list[str] = []
    for item in items:
        res = sanitize(item)
        clean.append(res.text)
        flags.extend(res.flags)
    return clean, flags


def contains_banned(text: str) -> bool:
    """Return ``True`` if ``text`` still contains any banned/blocked phrasing."""
    if not text:
        return False
    return any(p.search(text) for p, _ in _RULES) or any(p.search(text) for p in _HARD_BLOCK)
