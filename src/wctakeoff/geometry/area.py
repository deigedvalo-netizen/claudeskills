"""GeometryService: gross and net wall area derivation.

Requirement ids: FR-4, FR-8 (ADR-005, ADR-012, ARCH-A11).

Area derivation is blocked — MissingHeightError, never a default — when
the applied height is missing (ADR-005: flag rather than guess). A wall
with manual_area_sf set bypasses width x height (the ARCH-A11 escape
hatch for non-rectangular walls) and must carry a NON_RECTANGULAR flag.
Every produced area registers a TraceRecord (ADR-012) when a ledger is
attached.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from wctakeoff.domain.ids import new_value_id
from wctakeoff.domain.models import (
    AreaResult,
    Opening,
    OpeningPolicy,
    SourceRef,
    Wall,
)
from wctakeoff.geometry.openings import partition_openings, total_deducted_area_sf
from wctakeoff.trace.ledger import TraceLedger

_SQ_IN_PER_SF = Decimal(144)


class MissingHeightError(ValueError):
    """Raised when wall height is missing; no default is ever substituted."""


class GeometryService:
    """Derives wall areas under the opening-deduction policy (FR-4)."""

    def __init__(self, ledger: TraceLedger | None = None) -> None:
        self._ledger = ledger

    def compute_wall_area(
        self,
        wall: Wall,
        openings: Sequence[Opening],
        policy: OpeningPolicy,
    ) -> AreaResult:
        """compute_wall_area(wall, openings, policy) -> AreaResult

        Frozen interface ComputeWallArea (FR-4). Raises MissingHeightError
        when wall.height is None (ADR-005: block, never default). A wall
        carrying manual_area_sf uses it directly as gross and net basis
        before deductions (ARCH-A11 escape hatch; caller must have raised
        NON_RECTANGULAR).
        """
        deducted, skipped = partition_openings(openings, policy)
        deduction_sf = total_deducted_area_sf(deducted)

        if wall.manual_area_sf is not None:
            gross_sf = wall.manual_area_sf
            formula = "net_sf = manual_area_sf - sum(deducted openings)"
            inputs = {"manual_area_sf": gross_sf, "deducted_sf": deduction_sf}
        else:
            if wall.applied_height_in is None:
                raise MissingHeightError(
                    f"wall {wall.wall_id!r} in room {wall.room_id!r} has no "
                    "applied height; area derivation is blocked, no default "
                    "is assumed (FR-8, ADR-005)"
                )
            if wall.width_in is None:
                raise MissingHeightError(
                    f"wall {wall.wall_id!r} in room {wall.room_id!r} has no "
                    "width; area derivation is blocked, no default is "
                    "assumed (FR-8, ADR-005)"
                )
            gross_sf = (wall.width_in * wall.applied_height_in) / _SQ_IN_PER_SF
            formula = (
                "net_sf = (width_in * applied_height_in) / 144"
                " - sum(deducted openings)"
            )
            inputs = {
                "width_in": wall.width_in,
                "applied_height_in": wall.applied_height_in,
                "deducted_sf": deduction_sf,
            }

        net_sf = gross_sf - deduction_sf
        if net_sf < 0:
            net_sf = Decimal(0)

        if self._ledger is not None:
            self._ledger.record_trace(
                new_value_id(),
                formula,
                inputs,
                [SourceRef(sheet_id=None, read_method="geometry.compute_wall_area")],
            )

        return AreaResult(
            gross_sf=gross_sf,
            net_sf=net_sf,
            deducted=deducted,
            skipped=skipped,
        )
