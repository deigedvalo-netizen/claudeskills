"""Blanket-note parsing and wall-level override precedence.

Requirement ids: FR-3, FR-8 (ADR-008, ARCH-A4).

A room-level blanket note sets a default finish across that room's wall
set; a wall-level tag replaces the default for that wall only. Anything
that cannot be resolved unambiguously is routed to review, never
guessed.
"""
from __future__ import annotations

import re
from typing import Final

from wctakeoff.domain.units import ApplicationOrigin, V1_WC_TAGS

#: Matches a v1 WC tag anywhere in a note, e.g. "ALL WALLS: WC-1".
_WC_TAG_PATTERN: Final[re.Pattern[str]] = re.compile(r"\bWC-([0-9]+)\b", re.IGNORECASE)


def extract_wc_tag(note_text: str) -> str | None:
    """The single WC tag named by a note, or None when absent/ambiguous.

    A note naming zero tags or more than one distinct tag is ambiguous
    and must be flagged UNRESOLVED_UNO by the resolver (FR-8); this
    helper never picks a winner.
    """
    matches = {f"WC-{m.group(1)}" for m in _WC_TAG_PATTERN.finditer(note_text)}
    if len(matches) != 1:
        return None
    return matches.pop()


def is_v1_tag(wc_tag: str) -> bool:
    """True when the tag is in the v1 universe WC-1/WC-2/WC-3 (ARCH-A9)."""
    return wc_tag in V1_WC_TAGS


def origin_for(from_elevation: bool, is_override: bool) -> ApplicationOrigin:
    """Application origin per ADR-008 precedence bookkeeping."""
    if from_elevation:
        return ApplicationOrigin.ELEVATION_TAG
    if is_override:
        return ApplicationOrigin.WALL_OVERRIDE
    return ApplicationOrigin.ROOM_BLANKET
