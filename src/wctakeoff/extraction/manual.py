"""ManualEntryAdapter: the v1 ExtractionPort implementation.

Requirement ids: FR-2, FR-3, FR-4, NFR-3 (ADR-004).

Estimator-typed widths, heights, tags, openings and schedule fields,
entered against the displayed sheet and marked confirmed at source:
manual entry IS confirmation (ADR-011), so the v1 path satisfies NFR-4
trivially and is fully offline (NFR-3). This module never imports the
compute path.
"""
from __future__ import annotations

from decimal import Decimal

from wctakeoff.domain.ids import SheetId
from wctakeoff.domain.models import FieldRef, Proposal, Sheet


class ManualEntryAdapter:
    """Queues estimator-typed values and emits them as confirmed proposals."""

    _LABEL = "manual-entry"

    def __init__(self) -> None:
        self._queued: dict[SheetId, list[Proposal]] = {}

    def enter_value(
        self,
        sheet_id: SheetId,
        field_ref: FieldRef,
        value: object,
    ) -> Proposal:
        """Record one estimator-typed value against a displayed sheet.

        The proposal is confirmed at source (confidence 1): the human
        typed it while looking at the sheet (ADR-004, ADR-011).
        """
        proposal = Proposal(
            field_ref=field_ref,
            value=value,
            source_sheet_id=sheet_id,
            confidence=Decimal(1),
            confirmed=True,
        )
        self._queued.setdefault(sheet_id, []).append(proposal)
        return proposal

    def propose(self, sheet: Sheet) -> list[Proposal]:
        """ExtractionAdapter.propose: values entered against this sheet."""
        return list(self._queued.get(sheet.sheet_id, []))

    def source_label(self) -> str:
        """ExtractionAdapter.source_label."""
        return self._LABEL
