"""ConfirmationGate: provisional values become final only via confirmation.

Requirement ids: NFR-4, FR-8 (ADR-011).

Only ConfirmedValue instances may enter TakeoffEngine, and a takeoff is
finalisable only when no unconfirmed field and no blocking flag remains.
This is the single checkable choke point NFR-4 requires.
"""
from __future__ import annotations

import datetime as _dt

from wctakeoff.domain.ids import SetId
from wctakeoff.domain.models import (
    ConfirmedValue,
    FieldRef,
    FinalisationStatus,
    Proposal,
)
from wctakeoff.review.flags import FlagRegistry


class ConfirmationGate:
    """Tracks proposals awaiting confirmation and gates finalisation."""

    def __init__(self, flags: FlagRegistry) -> None:
        self._flags = flags
        self._pending: dict[tuple[str, str, str], Proposal] = {}
        self._confirmed: dict[tuple[str, str, str], ConfirmedValue] = {}

    @staticmethod
    def _key(field_ref: FieldRef) -> tuple[str, str, str]:
        return (
            field_ref.subject.kind,
            field_ref.subject.ref_id,
            field_ref.field_name,
        )

    def submit_proposal(self, proposal: Proposal) -> None:
        """Register an adapter proposal as pending until confirmed (NFR-4).

        A proposal arriving with confirmed=True (manual entry is
        confirmation at source, ADR-011) is promoted immediately.
        """
        if proposal.confirmed:
            self._confirmed[self._key(proposal.field_ref)] = ConfirmedValue(
                field_ref=proposal.field_ref,
                value=proposal.value,
                confirmed_by="manual-entry",
                confirmed_at=_dt.datetime.now(tz=_dt.timezone.utc),
            )
            self._pending.pop(self._key(proposal.field_ref), None)
        else:
            self._pending[self._key(proposal.field_ref)] = proposal

    def confirm_value(
        self, field_ref: FieldRef, value: object, confirmed_by: str
    ) -> ConfirmedValue:
        """confirm_value(field_ref, value, confirmed_by) -> ConfirmedValue

        Frozen interface ConfirmValue (NFR-4). Only ConfirmedValue
        instances may enter TakeoffEngine; this is the only way to
        produce one from a provisional read.
        """
        confirmed = ConfirmedValue(
            field_ref=field_ref,
            value=value,
            confirmed_by=confirmed_by,
            confirmed_at=_dt.datetime.now(tz=_dt.timezone.utc),
        )
        key = self._key(field_ref)
        self._confirmed[key] = confirmed
        self._pending.pop(key, None)
        return confirmed

    def is_takeoff_finalisable(self, set_id: SetId) -> FinalisationStatus:
        """is_takeoff_finalisable(set_id: SetId) -> FinalisationStatus

        Frozen interface IsTakeoffFinalisable (NFR-4, FR-8, ADR-011).
        Reports every unconfirmed field and every open blocking flag;
        finalisable only when both lists are empty. ExportService refuses
        to emit a final takeoff while either is non-empty.
        """
        unconfirmed = [p.field_ref for p in self._pending.values()]
        blocking = [
            f.flag_id
            for f in self._flags.open_blocking_flags()
            if f.flag_id is not None
        ]
        return FinalisationStatus(
            finalisable=not unconfirmed and not blocking,
            unconfirmed=unconfirmed,
            blocking=blocking,
        )

    def confirmed_value_for(self, field_ref: FieldRef) -> ConfirmedValue | None:
        """The confirmed value for a field, if the estimator confirmed one."""
        return self._confirmed.get(self._key(field_ref))
