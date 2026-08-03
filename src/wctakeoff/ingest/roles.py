"""Sheet role assignment and inference.

Requirement ids: FR-1 (AC-1.1, AC-1.3).

Roles may be inferred from the sheet number as a convenience but the
estimator's explicit assignment always wins; a sheet left UNASSIGNED is
flagged, never silently dropped.
"""
from __future__ import annotations

import re
from typing import Final

from wctakeoff.domain.units import SheetRole

#: Common drawing-number prefixes → role hints. Inference only; the
#: estimator's explicit assignment always overrides (FR-1).
_ROLE_HINTS: Final[list[tuple[re.Pattern[str], SheetRole]]] = [
    (re.compile(r"\bA?6\d{2}\b|SCHED", re.IGNORECASE), SheetRole.SCHEDULE),
    (re.compile(r"FINISH|FP-?\d|\bA?12\d\b", re.IGNORECASE), SheetRole.FINISH_PLAN),
    (re.compile(r"RCP|CEIL", re.IGNORECASE), SheetRole.CEILING_HEIGHT_PLAN),
    (re.compile(r"ELEV|INT-?\d|\bA?4\d{2}\b", re.IGNORECASE), SheetRole.ELEVATION),
]


def infer_role(sheet_number: str | None) -> SheetRole:
    """Best-effort role from a sheet number; UNASSIGNED when unclear.

    UNASSIGNED is a flagged condition, not a guess: an unclear number
    yields UNASSIGNED and the ingest service raises a flag for it.
    """
    if not sheet_number:
        return SheetRole.UNASSIGNED
    for pattern, role in _ROLE_HINTS:
        if pattern.search(sheet_number):
            return role
    return SheetRole.UNASSIGNED
