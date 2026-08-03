"""AggregationService: one order line per WC in that WC's own unit.

Requirement ids: FR-6, FR-5 (ADR-006, ADR-007, ADR-009, ADR-012).

Rolls every application of a WC across rooms, walls and sheets into a
single TakeoffLine, de-duplicating by (room_id, wall_id), rounding UP to
that WC's own sale unit and never converting between units. A line with
a non-empty blocked_by emits no quantity at all (ADR-005).
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Callable, Sequence

from wctakeoff.domain.ids import (
    ApplicationId,
    FlagId,
    new_value_id,
)
from wctakeoff.domain.models import (
    Application,
    QuantityResult,
    SourceRef,
    SubjectRef,
    TakeoffLine,
    WastePolicy,
)
from wctakeoff.aggregate.dedupe import dedupe_results, group_by_wc
from wctakeoff.math.rounding import DECIMAL_CONTEXT, round_up_to_sale_unit
from wctakeoff.review.flags import FlagRegistry
from wctakeoff.trace.ledger import TraceLedger

ApplicationLookup = Callable[[ApplicationId], Application | None]


class AggregationService:
    """Aggregates per-application quantities into per-WC lines (FR-6)."""

    def __init__(
        self,
        application_lookup: ApplicationLookup,
        flags: FlagRegistry | None = None,
        ledger: TraceLedger | None = None,
    ) -> None:
        self._lookup = application_lookup
        self._flags = flags
        self._ledger = ledger

    def aggregate_by_wc(
        self,
        results: Sequence[QuantityResult],
        policy: WastePolicy,
    ) -> list[TakeoffLine]:
        """aggregate_by_wc(results, policy) -> list[TakeoffLine]

        Frozen interface AggregateByWC (FR-6). De-duplicates by
        (room_id, wall_id); each TakeoffLine carries raw_qty,
        with_waste_qty and order_qty in that WC's own unit; never
        converts across units (ADR-007). order_qty is rounded UP to the
        sale unit, never down.
        """
        kept, _dropped = dedupe_results(results, self._lookup)
        lines: list[TakeoffLine] = []
        for wc_tag, group in sorted(group_by_wc(kept, self._lookup).items()):
            unit = group[0].unit
            blocked: list[FlagId] = []
            if self._flags is not None:
                blocked = [
                    f.flag_id
                    for f in self._flags.blocking_flags_for(
                        SubjectRef(kind="wc_definition", ref_id=wc_tag)
                    )
                    if f.flag_id is not None
                ]
            contributing = [
                r.application_id for r in group if r.application_id is not None
            ]
            if blocked:
                # A blocked line emits no quantity at all (ADR-005).
                lines.append(
                    TakeoffLine(
                        wc_tag=wc_tag,
                        contributing=contributing,
                        raw_qty=Decimal(0),
                        with_waste_qty=Decimal(0),
                        order_qty=Decimal(0),
                        unit=unit,
                        blocked_by=blocked,
                    )
                )
                continue
            with localcontext(DECIMAL_CONTEXT):
                raw = sum((r.raw_qty for r in group), Decimal(0))
                # Waste is applied exactly ONCE, here at the line level on
                # the raw (repeat-loss-inclusive) sum (ADR-006). Per-result
                # with_waste figures remain available for drill-down only.
                with_waste = raw * (Decimal(1) + policy.waste_for(wc_tag))
                order = round_up_to_sale_unit(with_waste)
            if self._ledger is not None:
                self._ledger.record_trace(
                    new_value_id(),
                    (
                        f"order_qty[{wc_tag}] = ceil(sum(with_waste_qty of "
                        f"{len(group)} contributing walls)) in {unit.value}"
                    ),
                    {"raw_qty": raw, "with_waste_qty": with_waste, "order_qty": order},
                    [SourceRef(sheet_id=None, read_method="aggregate.aggregate_by_wc")],
                )
            lines.append(
                TakeoffLine(
                    wc_tag=wc_tag,
                    contributing=contributing,
                    raw_qty=raw,
                    with_waste_qty=with_waste,
                    order_qty=order,
                    unit=unit,
                    blocked_by=[],
                )
            )
        return lines
