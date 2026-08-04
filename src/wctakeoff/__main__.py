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

from wctakeoff.domain.ids import (
    ApplicationId,
    OpeningId,
    RoomId,
    SetId,
    SheetId,
    WallId,
    new_set_id,
)
from wctakeoff.domain.models import (
    Application,
    Flag,
    Opening,
    QuantityResult,
    Room,
    SubjectRef,
    Wall,
)
from wctakeoff.domain.units import (
    UNKNOWN,
    ApplicationOrigin,
    FlagKind,
    MatchType,
    TakeoffMethod,
    UnitOfSale,
    Unknown,
    V1_WC_TAGS,
)
from wctakeoff.domain.wc_definition import SetReadRegistry, WCDefinition
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


def _str_field(values: dict[str, object], name: str) -> str | Unknown:
    value = values.get(name, UNKNOWN)
    return value if isinstance(value, str) and value else UNKNOWN


def _dec_field(values: dict[str, object], name: str) -> Decimal | Unknown:
    value = values.get(name, UNKNOWN)
    return value if isinstance(value, Decimal) else UNKNOWN


def _match_field(values: dict[str, object], name: str) -> MatchType | Unknown:
    value = values.get(name, UNKNOWN)
    return value if isinstance(value, MatchType) else UNKNOWN


def _opt_dec(values: dict[str, object], name: str) -> Decimal | None:
    value = values.get(name)
    return value if isinstance(value, Decimal) else None


def _ensure_flag(flags: FlagRegistry, flag: Flag) -> None:
    """Raise a flag unless an equivalent one is already open.

    Projection re-runs on every entry, so raising unconditionally would
    fill the review queue with duplicates of the same condition.
    """
    for existing in flags.open_flags():
        if (
            existing.kind is flag.kind
            and existing.subject_ref == flag.subject_ref
        ):
            return
    flags.raise_flag(flag)


def project_entered_values(
    set_id: SetId,
    ingest: SheetIngestService,
    adapter: ManualEntryAdapter,
    gate: ConfirmationGate,
    registry: SetReadRegistry,
    repository: ProjectRepository,
    flags: FlagRegistry | None = None,
) -> None:
    """Promote queued adapter proposals into registry + repository state.

    Requirement ids: FR-2, FR-3, FR-4, NFR-2, NFR-4 (ADR-004, ADR-009,
    ADR-011).

    This is step 3 of the spec's data flow: ExtractionPort proposals →
    ConfirmationGate → SetReadRegistry / ProjectRepository. Manual entry is
    confirmation at source (ADR-011), so every proposal the adapter holds is
    promoted by the gate on submission. Identities are derived from the
    estimator-typed room/wall designations rather than minted fresh, so
    repeated projection is idempotent and recomputation is reload-identical
    (NFR-2, ADR-009). Nothing is defaulted here: an absent SET READ field
    stays UNKNOWN and an unreadable dimension stays None, so the flag path
    still owns them (ADR-002, ADR-005).
    """
    wc_values: dict[str, dict[str, object]] = {}
    wc_sheets: dict[str, SheetId] = {}
    wall_values: dict[str, dict[str, object]] = {}
    wall_sheets: dict[str, SheetId] = {}
    opening_values: dict[str, dict[str, object]] = {}

    for sheet in ingest.all_sheets():
        for proposal in adapter.propose(sheet):
            gate.submit_proposal(proposal)
            subject = proposal.field_ref.subject
            field_name = proposal.field_ref.field_name
            if subject.kind == "wc_definition":
                wc_values.setdefault(subject.ref_id, {})[field_name] = (
                    proposal.value
                )
                wc_sheets[subject.ref_id] = proposal.source_sheet_id
            elif subject.kind == "wall":
                wall_values.setdefault(subject.ref_id, {})[field_name] = (
                    proposal.value
                )
                wall_sheets[subject.ref_id] = proposal.source_sheet_id
            elif subject.kind == "opening":
                opening_values.setdefault(subject.ref_id, {})[field_name] = (
                    proposal.value
                )

    for wc_tag, values in wc_values.items():
        if wc_tag not in V1_WC_TAGS:
            continue  # out of scope for v1 (ARCH-A9); never invented
        unit = values.get("unit_of_sale")
        if not isinstance(unit, UnitOfSale):
            continue  # unit of sale is read verbatim, never defaulted
        registry.upsert_wc_definition(
            WCDefinition(
                wc_tag=wc_tag,
                manufacturer=_str_field(values, "manufacturer"),
                pattern_name=_str_field(values, "pattern_name"),
                roll_width_in=_dec_field(values, "roll_width_in"),
                repeat_in=_dec_field(values, "repeat_in"),
                match_type=_match_field(values, "match_type"),
                unit_of_sale=unit,
                yield_per_unit=_dec_field(values, "yield_per_unit"),
                source_sheet_id=wc_sheets[wc_tag],
            )
        )

    openings_by_wall: dict[str, list[Opening]] = {}
    for ref_id, values in sorted(opening_values.items()):
        wall_ref, _, _label = ref_id.rpartition("/")
        width = _opt_dec(values, "width_in")
        height = _opt_dec(values, "height_in")
        if not wall_ref or width is None or height is None:
            continue  # an incomplete opening deducts nothing (ADR-005)
        kind = values.get("kind")
        openings_by_wall.setdefault(wall_ref, []).append(
            Opening(
                opening_id=OpeningId(ref_id),
                kind=kind if isinstance(kind, str) and kind else "OTHER",
                width_in=width,
                height_in=height,
            )
        )

    walls_by_room: dict[str, dict[str, Wall]] = {}
    applications: list[Application] = []
    for ref_id, values in wall_values.items():
        room_number, _, wall_designation = ref_id.partition("/")
        if not room_number or not wall_designation:
            continue
        room_id = RoomId(room_number)
        wall_id = WallId(wall_designation)
        manual_area = _opt_dec(values, "manual_area_sf")
        walls_by_room.setdefault(room_number, {})[wall_designation] = Wall(
            wall_id=wall_id,
            room_id=room_id,
            width_in=_opt_dec(values, "width_in"),
            applied_height_in=_opt_dec(values, "applied_height_in"),
            openings=openings_by_wall.get(ref_id, []),
            manual_area_sf=manual_area,
        )
        if manual_area is not None and flags is not None:
            # A traced area bypasses width x height, which is the ARCH-A11
            # escape hatch for non-rectangular walls; GeometryService
            # requires the caller to have flagged it as such.
            _ensure_flag(
                flags,
                Flag(
                    kind=FlagKind.NON_RECTANGULAR,
                    subject_ref=SubjectRef(kind="wall", ref_id=ref_id),
                    source_sheet_id=wall_sheets.get(ref_id),
                    blocks=[],
                    detail=(
                        f"wall {ref_id} uses a traced area of {manual_area} "
                        "sf measured on the drawing instead of width x "
                        "height; confirm the trace matches the wall "
                        "(ARCH-A2, ARCH-A11)"
                    ),
                ),
            )
        wall_tag = values.get("wc_tag")
        if isinstance(wall_tag, str) and wall_tag:
            applications.append(
                Application(
                    application_id=ApplicationId(f"{ref_id}/{wall_tag}"),
                    wc_tag=wall_tag,
                    room_id=room_id,
                    wall_id=wall_id,
                    origin=ApplicationOrigin.WALL_OVERRIDE,
                    source_sheet_id=wall_sheets[ref_id],
                )
            )

    repository.put_rooms(
        set_id,
        [
            Room(
                room_id=RoomId(room_number),
                room_number=room_number,
                walls=list(walls.values()),
            )
            for room_number, walls in walls_by_room.items()
        ],
    )
    repository.put_applications(set_id, applications)
    repository.put_definitions(set_id, registry.all_definitions())


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

    def commit_entered_values() -> None:
        """Projection hook for the shell (step 3 of the spec data flow)."""
        project_entered_values(
            set_id, ingest, adapter, gate, registry, repository, flags
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
                method = engine.select_takeoff_method(defn)
                if method is TakeoffMethod.STRIP and (
                    wall.width_in is None or wall.applied_height_in is None
                ):
                    # The strip method needs real width and height: drops
                    # come from width and the cut from height, so a traced
                    # area cannot stand in for them. Substituting zero here
                    # would emit a silent zero-quantity line, which is
                    # exactly what ADR-005 forbids.
                    _ensure_flag(
                        flags,
                        Flag(
                            kind=FlagKind.UNREADABLE_DIMENSION,
                            subject_ref=SubjectRef(
                                kind="wall",
                                ref_id=f"{room.room_number}/{wall.wall_id}",
                            ),
                            blocks=[str(app.application_id)],
                            detail=(
                                f"{defn.wc_tag} is a patterned strip "
                                "material, so wall "
                                f"{room.room_number}/{wall.wall_id} needs "
                                "both a width and an applied height; a "
                                "traced area alone cannot determine drops. "
                                "Measure or type both (FR-4, ADR-005)"
                            ),
                        ),
                    )
                    continue
                area = geometry.compute_wall_area(wall, wall.openings, opening)
                results.append(
                    engine.compute_for_application(
                        app,
                        defn,
                        wall.width_in if wall.width_in is not None else Decimal(0),
                        wall.applied_height_in
                        if wall.applied_height_in is not None
                        else Decimal(0),
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
        on_entry_committed=commit_entered_values,
    )
    shell.recompute()
    shell.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
