"""Policy panel: explicit takeoff settings, never hard-coded.

Requirement ids: FR-4, FR-5, NFR-2 (ADR-010, ARCH-A5).

Waste percentage, opening deduction toggle and threshold, and trim
allowance, edited here and captured as a snapshot per computed result.
The panel contains no takeoff arithmetic.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wctakeoff.domain.ids import SetId
from wctakeoff.policy.settings import PolicyStore


class PolicyPanel(QWidget):
    """Edits the PolicyStore settings for the open set (ADR-010)."""

    def __init__(
        self,
        store: PolicyStore,
        set_id: SetId,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._store = store
        self._set_id = set_id
        self._on_changed = on_changed

        snapshot = store.get_policy_snapshot(set_id)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.waste_pct = QLineEdit(str(snapshot.waste_pct))
        self.deduct_openings = QCheckBox("Deduct openings at/above threshold")
        self.deduct_openings.setChecked(snapshot.deduct_openings)
        self.threshold_sf = QLineEdit(str(snapshot.opening_threshold_sf))
        self.trim_allowance_in = QLineEdit(str(snapshot.trim_allowance_in))
        form.addRow("Waste fraction (e.g. 0.10)", self.waste_pct)
        form.addRow(self.deduct_openings)
        form.addRow("Opening threshold (sf)", self.threshold_sf)
        form.addRow("Trim allowance (in)", self.trim_allowance_in)
        layout.addLayout(form)
        self.apply = QPushButton("Apply policy (recomputes all quantities)")
        self.apply.clicked.connect(self._on_apply)
        layout.addWidget(self.apply)

    @staticmethod
    def _parse(text: str, fallback: Decimal) -> Decimal:
        try:
            return Decimal(text.strip())
        except InvalidOperation:
            return fallback

    def _on_apply(self) -> None:
        current = self._store.get_policy_snapshot(self._set_id)
        self._store.set_policy(
            self._set_id,
            waste_pct=self._parse(self.waste_pct.text(), current.waste_pct),
            per_wc_waste=dict(current.per_wc_waste),
            deduct_openings=self.deduct_openings.isChecked(),
            opening_threshold_sf=self._parse(
                self.threshold_sf.text(), current.opening_threshold_sf
            ),
            trim_allowance_in=self._parse(
                self.trim_allowance_in.text(), current.trim_allowance_in
            ),
        )
        if self._on_changed is not None:
            self._on_changed()
