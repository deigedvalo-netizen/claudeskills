"""Zoomable sheet viewer widget.

Requirement ids: FR-1, FR-7 (ADR-001).

A QGraphicsView-based viewer for the ingested PNG sheets with wheel
zoom, so the estimator enters values against the displayed sheet.
Contains no takeoff arithmetic.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from wctakeoff.domain.models import Sheet

_ZOOM_IN_FACTOR = 1.25


class SheetViewer(QGraphicsView):
    """Displays one sheet at a time with wheel zoom (FR-1)."""

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._pixmap_item: QGraphicsPixmapItem | None = None

    def show_sheet(self, sheet: Sheet) -> None:
        """Load and display a sheet's PNG."""
        self._scene.clear()
        pixmap = QPixmap(str(sheet.path))
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt API)
        """Zoom with the mouse wheel."""
        factor = (
            _ZOOM_IN_FACTOR
            if event.angleDelta().y() > 0
            else 1 / _ZOOM_IN_FACTOR
        )
        self.scale(factor, factor)
