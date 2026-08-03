"""PolicyStore: takeoff settings as explicit configuration.

Requirement ids: FR-4, FR-5, NFR-2 (ADR-010).

Waste percentage (global with optional per-WC override), the
opening-deduction toggle and its area threshold, and the trim allowance
are configuration, never hard-coded constants. Every computed result
records the PolicySnapshot it was produced under, so results stay
explainable and reproducible after a default changes.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from wctakeoff.domain.ids import SetId
from wctakeoff.domain.models import OpeningPolicy, PolicySnapshot, WastePolicy


class PolicyStore:
    """Holds per-set takeoff policy and serves immutable snapshots."""

    def __init__(self) -> None:
        self._policies: dict[SetId, PolicySnapshot] = {}

    def set_policy(
        self,
        set_id: SetId,
        *,
        waste_pct: Decimal = Decimal("0.10"),
        per_wc_waste: Mapping[str, Decimal] | None = None,
        deduct_openings: bool = True,
        opening_threshold_sf: Decimal = Decimal("20"),
        trim_allowance_in: Decimal = Decimal("0"),
    ) -> PolicySnapshot:
        """Replace the active policy for a set (estimator edit, FR-4/FR-5)."""
        snapshot = PolicySnapshot(
            waste_pct=waste_pct,
            per_wc_waste=dict(per_wc_waste or {}),
            deduct_openings=deduct_openings,
            opening_threshold_sf=opening_threshold_sf,
            trim_allowance_in=trim_allowance_in,
        )
        self._policies[set_id] = snapshot
        return snapshot

    def get_policy_snapshot(self, set_id: SetId) -> PolicySnapshot:
        """get_policy_snapshot(set_id: SetId) -> PolicySnapshot

        Frozen interface GetPolicySnapshot (FR-4, FR-5, NFR-2, ADR-010).
        A set with no explicit edits gets the documented defaults
        (deduct ON at 20 sf, waste 0.10, trim 0) — these are defaults of
        POLICY configuration, not imputed set-read values (ARCH-A5).
        """
        if set_id not in self._policies:
            self._policies[set_id] = PolicySnapshot()
        return self._policies[set_id]

    @staticmethod
    def opening_policy(snapshot: PolicySnapshot) -> OpeningPolicy:
        """The opening-deduction slice geometry consumes (FR-4)."""
        return OpeningPolicy(
            deduct_openings=snapshot.deduct_openings,
            opening_threshold_sf=snapshot.opening_threshold_sf,
        )

    @staticmethod
    def waste_policy(snapshot: PolicySnapshot) -> WastePolicy:
        """The waste/trim slice the math core consumes (FR-5)."""
        return WastePolicy(
            waste_pct=snapshot.waste_pct,
            per_wc_waste=dict(snapshot.per_wc_waste),
            trim_allowance_in=snapshot.trim_allowance_in,
        )
