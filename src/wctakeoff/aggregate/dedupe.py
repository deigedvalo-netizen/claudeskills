"""(room_id, wall_id) de-duplication for cross-sheet aggregation.

Requirement ids: FR-6, FR-4, FR-8 (ADR-009).

The same physical wall commonly appears on both the finish plan and an
elevation; counting it from each sheet double-counts material. Wall
identity is (room_id, wall_id), and aggregation keeps exactly one
contribution per identity per WC.
"""
from __future__ import annotations

from typing import Callable, Iterable, Sequence

from wctakeoff.domain.ids import ApplicationId, RoomId, WallId
from wctakeoff.domain.models import Application, QuantityResult

#: Injected lookup from application_id to its Application record.
ApplicationLookup = Callable[[ApplicationId], Application | None]


def dedupe_results(
    results: Sequence[QuantityResult],
    lookup: ApplicationLookup,
) -> tuple[list[QuantityResult], list[QuantityResult]]:
    """Split results into (kept, dropped) by (room_id, wall_id) identity.

    The first result per (wc_tag, room_id, wall_id) identity is kept and
    later duplicates are dropped (AC-6.2, ADR-009). A result whose
    application cannot be resolved is dropped as unattributable — an
    upstream defect, never silently counted.
    """
    kept: list[QuantityResult] = []
    dropped: list[QuantityResult] = []
    seen: set[tuple[str, RoomId, WallId]] = set()
    for result in results:
        app = lookup(result.application_id) if result.application_id else None
        if app is None:
            dropped.append(result)
            continue
        identity = (app.wc_tag, app.room_id, app.wall_id)
        if identity in seen:
            dropped.append(result)
            continue
        seen.add(identity)
        kept.append(result)
    return kept, dropped


def group_by_wc(
    results: Iterable[QuantityResult],
    lookup: ApplicationLookup,
) -> dict[str, list[QuantityResult]]:
    """Group de-duplicated results by their WC tag for line rollup (FR-6)."""
    groups: dict[str, list[QuantityResult]] = {}
    for result in results:
        app = lookup(result.application_id) if result.application_id else None
        if app is None:
            continue
        groups.setdefault(app.wc_tag, []).append(result)
    return groups
