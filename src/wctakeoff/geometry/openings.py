"""Opening-deduction policy application.

Requirement ids: FR-4 (ARCH-A5, ADR-010).

Openings at or above the policy threshold are deducted; smaller ones are
not deducted but ARE itemised as skipped, so the drill-down can show
every deduction taken or skipped (NFR-1). The threshold and the on/off
toggle come from policy configuration, never a hard-coded constant.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from wctakeoff.domain.models import Opening, OpeningPolicy


def partition_openings(
    openings: Sequence[Opening], policy: OpeningPolicy
) -> tuple[list[Opening], list[Opening]]:
    """Split openings into (deducted, skipped) under the policy (FR-4).

    With deduction off, every opening is skipped (itemised, not deducted).
    With deduction on, an opening is deducted when its area meets or
    exceeds the threshold; below-threshold openings are skipped but
    itemised (ARCH-A5).
    """
    if not policy.deduct_openings:
        return [], list(openings)
    deducted: list[Opening] = []
    skipped: list[Opening] = []
    for opening in openings:
        if opening.area_sf >= policy.opening_threshold_sf:
            deducted.append(opening)
        else:
            skipped.append(opening)
    return deducted, skipped


def total_deducted_area_sf(deducted: Sequence[Opening]) -> Decimal:
    """Sum of the deducted opening areas in square feet."""
    total = Decimal(0)
    for opening in deducted:
        total += opening.area_sf
    return total
