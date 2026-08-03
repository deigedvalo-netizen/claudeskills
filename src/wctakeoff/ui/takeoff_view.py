"""Per-WC takeoff view with drill-down to the math behind each number.

Requirement ids: FR-7, NFR-1 (ADR-012).

One order line per WC with raw, with-waste and order quantities in that
WC's own unit; expanding a line shows the contributing per-wall results
(method, drops, cut length, net area). Displayed values resolve through
the trace ledger; the widget renders, it never computes.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from wctakeoff.presentation.presenter import TakeoffView, format_qty


class TakeoffViewWidget(QWidget):
    """Renders a TakeoffView read-model (FR-7); no arithmetic here."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._heading = QLabel("Takeoff — one line per WC, per-WC units only")
        layout.addWidget(self._heading)
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(
            ["WC / Wall", "Raw", "With Waste", "Order (UP)", "Unit / Method"]
        )
        layout.addWidget(self._tree)

    def show_view(self, view: TakeoffView) -> None:
        """Render the read-model built by TakeoffPresenter."""
        self._tree.clear()
        for line_view in view.lines:
            line = line_view.line
            if line.blocked_by:
                top = QTreeWidgetItem(
                    [
                        line.wc_tag,
                        "—",
                        "—",
                        "BLOCKED",
                        f"{len(line.blocked_by)} blocking flag(s)",
                    ]
                )
            else:
                top = QTreeWidgetItem(
                    [
                        line.wc_tag,
                        format_qty(line.raw_qty),
                        format_qty(line.with_waste_qty),
                        format_qty(line.order_qty),
                        line.unit.value,
                    ]
                )
            for result in line_view.contributing_results:
                detail = QTreeWidgetItem(
                    [
                        f"app {result.application_id or '?'}",
                        format_qty(result.raw_qty),
                        format_qty(result.with_waste_qty),
                        (
                            f"drops={result.drops} "
                            f"cut={format_qty(result.cut_length_in)}in"
                            if result.drops is not None
                            and result.cut_length_in is not None
                            else f"net={format_qty(result.net_area_sf)}sf"
                        ),
                        result.method.value,
                    ]
                )
                top.addChild(detail)
            self._tree.addTopLevelItem(top)
        self._tree.expandAll()
