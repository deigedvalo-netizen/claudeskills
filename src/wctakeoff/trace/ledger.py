"""TraceLedger: every computed number registers its derivation.

Requirement ids: NFR-1, FR-7 (ADR-012).

No black-box totals: each displayed value resolves through explain_value
to the formula applied, the named inputs consumed, and a source reference
per input. An unresolvable value_id is a defect, so explain_value raises
rather than returning a placeholder. The ledger is invalidated and
rebuilt on every edit-triggered recompute (ADR-012).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from wctakeoff.domain.ids import ValueId
from wctakeoff.domain.models import SourceRef, TraceRecord


class UnresolvableValueError(LookupError):
    """A displayed value_id with no trace record — a defect per ADR-012."""


class TraceLedger:
    """In-memory ledger of TraceRecords keyed by value_id (NFR-1)."""

    def __init__(self) -> None:
        self._records: dict[ValueId, TraceRecord] = {}

    def record_trace(
        self,
        value_id: ValueId,
        formula: str,
        inputs: Mapping[str, Decimal],
        sources: Sequence[SourceRef],
    ) -> TraceRecord:
        """record_trace(value_id, formula, inputs, sources) -> TraceRecord

        Frozen interface RecordTrace (NFR-1). Re-recording a value_id
        replaces its prior record: an edit-triggered recompute rebuilds
        the ledger entry for every dependent value.
        """
        record = TraceRecord(
            value_id=value_id,
            formula=formula,
            inputs=dict(inputs),
            sources=list(sources),
        )
        self._records[value_id] = record
        return record

    def explain_value(self, value_id: ValueId) -> TraceRecord:
        """explain_value(value_id: ValueId) -> TraceRecord

        Frozen interface ExplainValue (NFR-1, FR-7). Every displayed
        number must resolve; an unresolvable value_id raises
        UnresolvableValueError and must be treated as a defect, never
        rendered bare.
        """
        try:
            return self._records[value_id]
        except KeyError as exc:
            raise UnresolvableValueError(
                f"value_id {value_id!r} has no trace record; a displayed "
                "value without a derivation is a defect (ADR-012)"
            ) from exc

    def invalidate(self, value_id: ValueId) -> None:
        """Drop one record ahead of a recompute of that value."""
        self._records.pop(value_id, None)

    def clear(self) -> None:
        """Drop all records ahead of a full recompute (ADR-012)."""
        self._records.clear()
