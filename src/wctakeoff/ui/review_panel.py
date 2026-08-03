"""Review-queue panel: the live list of blocking and advisory flags.

Requirement ids: FR-8, FR-7 (ADR-005).

Shows every open flag with its kind, subject, originating sheet and what
it blocks. Resolving happens by fixing the underlying input; the panel
is read-only over the registry and contains no takeoff arithmetic.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from wctakeoff.review.flags import FlagRegistry


class ReviewPanel(QWidget):
    """Docked review queue (FR-8): flag rather than guess, visibly."""

    def __init__(self, flags: FlagRegistry) -> None:
        super().__init__()
        self._flags = flags
        layout = QVBoxLayout(self)
        self._summary = QLabel("")
        layout.addWidget(self._summary)
        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Kind", "Subject", "Blocks", "Detail"])
        layout.addWidget(self._tree)
        self.refresh()

    def refresh(self) -> None:
        """Re-read the registry; called after any edit or recompute."""
        self._tree.clear()
        open_flags = self._flags.open_flags()
        blocking = sum(1 for f in open_flags if f.blocks)
        self._summary.setText(
            f"{len(open_flags)} open flag(s), {blocking} blocking. "
            "A blocking flag prevents its dependent quantity entirely."
        )
        for flag in open_flags:
            item = QTreeWidgetItem(
                [
                    flag.kind.value,
                    f"{flag.subject_ref.kind}:{flag.subject_ref.ref_id}",
                    ", ".join(flag.blocks) if flag.blocks else "—",
                    flag.detail,
                ]
            )
            self._tree.addTopLevelItem(item)
