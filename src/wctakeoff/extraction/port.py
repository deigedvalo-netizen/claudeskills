"""ExtractionPort: the single boundary through which all reading enters.

Requirement ids: FR-3, FR-4, NFR-4 (ADR-004, ADR-011).

Every adapter yields Proposal objects carrying source, confidence and
confirmed=False by default. No adapter may import or invoke the compute
path (TakeoffEngine); the guarantee that a reader cannot compute is
structural. Frozen interface ExtractionAdapter.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from wctakeoff.domain.models import Proposal, Sheet


@runtime_checkable
class ExtractionAdapter(Protocol):
    """class ExtractionAdapter(Protocol):
        def propose(self, sheet: Sheet) -> list[Proposal]
        def source_label(self) -> str

    Frozen interface ExtractionAdapter (FR-3, FR-4, NFR-4). Proposal
    {field_ref, value, source_sheet_id, confidence: Decimal,
    confirmed: bool = False}.
    """

    def propose(self, sheet: Sheet) -> list[Proposal]:
        """Provisional values read from one sheet; never final (NFR-4)."""
        ...

    def source_label(self) -> str:
        """Human-readable label naming where these proposals come from."""
        ...
