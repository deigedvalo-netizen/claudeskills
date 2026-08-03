"""TakeoffEngine: the pure, I/O-free quantity core.

Requirement ids: FR-5, NFR-2 (ADR-003, ADR-005, ADR-006).

The engine has no I/O, no clock, no randomness and no global state. It
consults blocking_flags_for (injected as a pure callable, keeping the
core free of registry imports) before computing, and refuses to produce
any quantity for a blocked subject: a blocked item yields no number at
all, never a partial or estimated one (ADR-005).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

from wctakeoff.domain.ids import ApplicationId
from wctakeoff.domain.models import (
    Application,
    Flag,
    QuantityResult,
    SubjectRef,
    WastePolicy,
)
from wctakeoff.domain.units import TakeoffMethod
from wctakeoff.domain.wc_definition import WCDefinition
from wctakeoff.math import methods

#: Pure lookup injected by the composition root; the engine never imports
#: the flag registry (ADR-002 one-way dependency, ADR-003 purity).
BlockingFlagsFn = Callable[[SubjectRef], Sequence[Flag]]


class BlockedSubjectError(ValueError):
    """Raised when a quantity is requested for a flagged, blocked subject."""

    def __init__(self, subject: SubjectRef, flags: Sequence[Flag]) -> None:
        self.subject = subject
        self.flags = list(flags)
        super().__init__(
            f"subject {subject.kind}:{subject.ref_id} has "
            f"{len(self.flags)} blocking flag(s); no quantity is emitted "
            "(FR-8, ADR-005)"
        )


class TakeoffEngine:
    """Selects the method and computes per-application quantities (FR-5)."""

    def __init__(self, blocking_flags_for: BlockingFlagsFn | None = None) -> None:
        self._blocking_flags_for = blocking_flags_for

    def _check_not_blocked(self, subject: SubjectRef) -> None:
        if self._blocking_flags_for is None:
            return
        flags = self._blocking_flags_for(subject)
        if flags:
            raise BlockedSubjectError(subject, flags)

    def select_takeoff_method(self, defn: WCDefinition) -> TakeoffMethod:
        """Frozen interface SelectTakeoffMethod (FR-5); delegates to the
        pure method module."""
        return methods.select_takeoff_method(defn)

    def compute_quantity_strip(
        self,
        wall_width_in: Decimal,
        wall_height_in: Decimal,
        defn: WCDefinition,
        policy: WastePolicy,
    ) -> QuantityResult:
        """Frozen interface ComputeQuantityStrip (FR-5, ADR-006)."""
        self._check_not_blocked(SubjectRef(kind="wc_definition", ref_id=defn.wc_tag))
        return methods.compute_quantity_strip(
            wall_width_in, wall_height_in, defn, policy
        )

    def compute_quantity_area(
        self,
        net_area_sf: Decimal,
        defn: WCDefinition,
        policy: WastePolicy,
    ) -> QuantityResult:
        """Frozen interface ComputeQuantityArea (FR-5, ADR-006)."""
        self._check_not_blocked(SubjectRef(kind="wc_definition", ref_id=defn.wc_tag))
        return methods.compute_quantity_area(net_area_sf, defn, policy)

    def compute_for_application(
        self,
        application: Application,
        defn: WCDefinition,
        wall_width_in: Decimal,
        wall_height_in: Decimal,
        net_area_sf: Decimal,
        policy: WastePolicy,
    ) -> QuantityResult:
        """Compute the quantity for one application, attaching its id.

        The frozen compute_quantity_* signatures carry no application
        identity, so this composition helper stamps application_id onto
        the returned QuantityResult for aggregation (FR-6).
        """
        self._check_not_blocked(
            SubjectRef(kind="application", ref_id=str(application.application_id))
        )
        method = self.select_takeoff_method(defn)
        if method is TakeoffMethod.STRIP:
            result = self.compute_quantity_strip(
                wall_width_in, wall_height_in, defn, policy
            )
        else:
            result = self.compute_quantity_area(net_area_sf, defn, policy)
        stamped: ApplicationId = application.application_id
        return result.model_copy(update={"application_id": stamped})
