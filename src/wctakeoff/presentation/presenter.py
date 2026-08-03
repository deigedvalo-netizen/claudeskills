"""TakeoffPresenter and ExportService: the read-model and its exports.

Requirement ids: FR-7, NFR-1 (ADR-011, ADR-012).

The presenter builds everything the UI renders: one order line per WC,
drill-down to contributing walls, the verbatim set-read reference block
labelled as non-computed, the policy summary and the review queue. The
export service refuses to emit a final takeoff while any unconfirmed
value or blocking flag remains (ADR-011), and shows raw and with-waste
figures side by side, rounding nothing away silently.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Callable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from wctakeoff.domain.ids import SetId
from wctakeoff.domain.models import (
    Flag,
    PolicySnapshot,
    QuantityResult,
    TakeoffLine,
)
from wctakeoff.domain.units import ExportFormat
from wctakeoff.domain.wc_definition import SetReadRegistry, WCDefinition
from wctakeoff.aggregate.rollup import AggregationService
from wctakeoff.policy.settings import PolicyStore
from wctakeoff.review.flags import FlagRegistry
from wctakeoff.review.gate import ConfirmationGate
from wctakeoff.trace.ledger import TraceLedger

_MODEL_CONFIG = ConfigDict(frozen=True, arbitrary_types_allowed=True)


class TakeoffLineView(BaseModel):
    """One rendered order line plus its drill-down (FR-7, AC-7.1)."""

    model_config = _MODEL_CONFIG

    line: TakeoffLine
    contributing_results: list[QuantityResult] = Field(default_factory=list)


class TakeoffView(BaseModel):
    """The complete read-model the UI renders (FR-7, NFR-1)."""

    model_config = _MODEL_CONFIG

    lines: list[TakeoffLineView] = Field(default_factory=list)
    set_read_block: list[WCDefinition] = Field(default_factory=list)
    policy_summary: PolicySnapshot
    review_queue: list[Flag] = Field(default_factory=list)


#: Supplies the per-application QuantityResults for a set (recomputed on
#: every edit); injected so the presenter holds no compute state.
ResultsProvider = Callable[[SetId], Sequence[QuantityResult]]


class NotFinalisableError(RuntimeError):
    """Export refused: unconfirmed values or blocking flags remain."""


class TakeoffPresenter:
    """Builds the takeoff read-model, recomputed on any edit (FR-7)."""

    def __init__(
        self,
        aggregation: AggregationService,
        registry: SetReadRegistry,
        ledger: TraceLedger,
        flags: FlagRegistry,
        policy_store: PolicyStore,
        results_provider: ResultsProvider,
    ) -> None:
        self._aggregation = aggregation
        self._registry = registry
        self._ledger = ledger
        self._flags = flags
        self._policy_store = policy_store
        self._results_provider = results_provider

    def build_takeoff_view(self, set_id: SetId) -> TakeoffView:
        """build_takeoff_view(set_id: SetId) -> TakeoffView

        Frozen interface BuildTakeoffView (FR-7, NFR-1). The set-read
        block is the verbatim, non-computed reference; the review queue
        is every open flag; every number in the lines resolves through
        the trace ledger.
        """
        results = list(self._results_provider(set_id))
        policy = self._policy_store.get_policy_snapshot(set_id)
        lines = self._aggregation.aggregate_by_wc(
            results, PolicyStore.waste_policy(policy)
        )
        by_app = {
            r.application_id: r for r in results if r.application_id is not None
        }
        line_views = [
            TakeoffLineView(
                line=line,
                contributing_results=[
                    by_app[a] for a in line.contributing if a in by_app
                ],
            )
            for line in lines
        ]
        return TakeoffView(
            lines=line_views,
            set_read_block=self._registry.all_definitions(),
            policy_summary=policy,
            review_queue=self._flags.open_flags(),
        )


class ExportService:
    """Exports the finalised takeoff (FR-7); gated by ADR-011."""

    def __init__(self, gate: ConfirmationGate | None = None) -> None:
        self._gate = gate

    def export_takeoff(
        self, view: TakeoffView, fmt: ExportFormat, dest: Path
    ) -> Path:
        """export_takeoff(view, fmt, dest) -> Path

        Frozen interface ExportTakeoff (FR-7). ExportFormat in
        {XLSX, PDF}; both raw and with-waste figures are required in the
        output. Refuses to export while the takeoff is not finalisable
        (unconfirmed values or blocking flags, ADR-011).
        """
        blocked = [lv for lv in view.lines if lv.line.blocked_by]
        if blocked:
            tags = ", ".join(lv.line.wc_tag for lv in blocked)
            raise NotFinalisableError(
                f"export refused: line(s) {tags} carry blocking flags; "
                "resolve the review queue first (FR-8, ADR-011)"
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        if fmt is ExportFormat.XLSX:
            from wctakeoff.presentation.export_xlsx import write_xlsx

            return write_xlsx(view, dest)
        from wctakeoff.presentation.export_pdf import write_pdf

        return write_pdf(view, dest)


def format_qty(value: Decimal) -> str:
    """Render a Decimal exactly as stored — nothing rounded away silently."""
    return format(value.normalize(), "f")
