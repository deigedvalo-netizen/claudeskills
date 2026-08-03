"""Application entry point: composition root for the desktop monolith.

Requirement ids: FR-1, FR-7, NFR-3 (ADR-001, ADR-004).

Wires the layered components — repository, registries, geometry, the
pure math core, aggregation, presenter and shell — into one offline
desktop process. The v1 extraction adapter is manual entry only
(ADR-004); no network client is imported on any path here (NFR-3).
"""
from __future__ import annotations

import sys
from decimal import Decimal
from typing import Sequence

from wctakeoff.domain.ids import ApplicationId, SetId, new_set_id
from wctakeoff.domain.models import Application, QuantityResult
from wctakeoff.domain.wc_definition import SetReadRegistry
from wctakeoff.aggregate.rollup import AggregationService
from wctakeoff.extraction.manual import ManualEntryAdapter
from wctakeoff.geometry.area import GeometryService, MissingHeightError
from wctakeoff.ingest.sheets import SheetIngestService
from wctakeoff.math.engine import BlockedSubjectError, TakeoffEngine
from wctakeoff.math.methods import BlockedInputError
from wctakeoff.persistence.repository import ProjectRepository
from wctakeoff.policy.settings import PolicyStore
from wctakeoff.presentation.presenter import ExportService, TakeoffPresenter
from wctakeoff.review.flags import FlagRegistry
from wctakeoff.review.gate import ConfirmationGate
from wctakeoff.trace.ledger import TraceLedger


def main() -> int:
    """Launch the wallcovering takeoff desktop application."""
    from PySide6.QtWidgets import QApplication

    from wctakeoff.ui.main_window import DesktopShell

    repository = ProjectRepository()
    flags = FlagRegistry()
    ledger = TraceLedger()
    registry = SetReadRegistry()
    policy_store = PolicyStore()
    gate = ConfirmationGate(flags)
    ingest = SheetIngestService(flags)
    adapter = ManualEntryAdapter()
    geometry = GeometryService(ledger)
    engine = TakeoffEngine(blocking_flags_for=flags.blocking_flags_for)

    set_id: SetId = new_set_id()

    def application_lookup(app_id: ApplicationId) -> Application | None:
        for app in repository.applications_for(set_id):
            if app.application_id == app_id:
                return app
        return None

    aggregation = AggregationService(
        application_lookup, flags=flags, ledger=ledger
    )

    def results_provider(current_set: SetId) -> Sequence[QuantityResult]:
        """Recompute every unblocked application's quantity (AC-7.2)."""
        snapshot = policy_store.get_policy_snapshot(current_set)
        waste = PolicyStore.waste_policy(snapshot)
        opening = PolicyStore.opening_policy(snapshot)
        rooms = {r.room_id: r for r in repository.rooms_for(current_set)}
        results: list[QuantityResult] = []
        for app in repository.applications_for(current_set):
            defn = registry.get_wc_definition(app.wc_tag)
            room = rooms.get(app.room_id)
            if defn is None or room is None:
                continue  # flagged upstream; no quantity is fabricated
            wall = next(
                (w for w in room.walls if w.wall_id == app.wall_id), None
            )
            if wall is None:
                continue
            try:
                area = geometry.compute_wall_area(wall, wall.openings, opening)
                results.append(
                    engine.compute_for_application(
                        app,
                        defn,
                        wall.width_in or Decimal(0),
                        wall.applied_height_in or Decimal(0),
                        area.net_sf,
                        waste,
                    )
                )
            except (MissingHeightError, BlockedInputError, BlockedSubjectError):
                # Blocked items yield no number at all (ADR-005); the
                # corresponding flags are already in the review queue.
                continue
        return results

    presenter = TakeoffPresenter(
        aggregation, registry, ledger, flags, policy_store, results_provider
    )
    export_service = ExportService(gate)

    app = QApplication(sys.argv)
    shell = DesktopShell(
        set_id,
        ingest,
        adapter,
        presenter,
        policy_store,
        flags,
        gate,
        export_service,
    )
    shell.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
