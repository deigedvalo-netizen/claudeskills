"""Zoomable sheet viewer with scale calibration and measurement.

Requirement ids: FR-1, FR-4, FR-7 (ADR-001, ARCH-A2, ADR-005).

A QGraphicsView-based viewer for the ingested sheets with wheel zoom, plus
the on-drawing measuring tools: calibrate a sheet's scale against one of
its own printed dimensions, then measure wall lengths and traced areas in
real-world units.

ARCH-A2 is respected rather than circumvented: the scale is never derived
from page geometry, it is derived from a printed dimension the estimator
identifies and types, and every measured value is emitted as a labelled
measurement for the estimator to confirm into a field, never written
silently into the takeoff. A sheet with no calibration refuses to measure
instead of assuming a scale (ADR-005). Contains no takeoff arithmetic.
"""
from __future__ import annotations

import enum
from typing import Final

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPen,
    QPixmap,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QInputDialog,
    QMessageBox,
)

from wctakeoff.domain.models import Sheet
from wctakeoff.ui.measure import (
    Calibration,
    LengthParseError,
    Point,
    ScaleUncalibratedError,
    calibrate,
    format_area_sf,
    format_inches,
    from_float,
    measure_area_sf,
    measure_length_inches,
    parse_length_inches,
)

_ZOOM_IN_FACTOR = 1.25

_CALIBRATION_COLOUR: Final[str] = "#0a7d2c"
_DISTANCE_COLOUR: Final[str] = "#c1121f"
_AREA_COLOUR: Final[str] = "#1d4ed8"


class ViewerMode(enum.Enum):
    """What a left-click on the sheet currently does."""

    PAN = "PAN"
    CALIBRATE = "CALIBRATE"
    DISTANCE = "DISTANCE"
    AREA = "AREA"


class SheetViewer(QGraphicsView):
    """Displays one sheet at a time with zoom and measuring tools."""

    #: Scale established for the displayed sheet; carries a provenance line.
    calibrated = Signal(str)
    #: A measured wall length, in inches, as a Decimal.
    distance_measured = Signal(object)
    #: A measured traced area, in square feet, as a Decimal.
    area_measured = Signal(object)
    #: Short guidance for the status bar.
    status = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._mode = ViewerMode.PAN
        self._sheet_id: str | None = None
        self._calibrations: dict[str, Calibration] = {}
        self._pending: list[Point] = []
        self._overlay: list[QGraphicsItem] = []

    # -- sheet display ----------------------------------------------------

    def show_sheet(self, sheet: Sheet) -> None:
        """Load and display a sheet, restoring any scale it already has."""
        self._scene.clear()
        self._overlay = []
        self._pending = []
        self._sheet_id = str(sheet.sheet_id)
        pixmap = QPixmap(str(sheet.path))
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.status.emit(self._prompt())

    def calibration(self) -> Calibration | None:
        """The displayed sheet's scale, if one has been established."""
        if self._sheet_id is None:
            return None
        return self._calibrations.get(self._sheet_id)

    def set_mode(self, mode: ViewerMode) -> None:
        """Switch what a left-click does, discarding any partial measure."""
        self._mode = mode
        self._pending = []
        if mode is ViewerMode.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.status.emit(self._prompt())

    def clear_measurements(self) -> None:
        """Remove drawn measurement overlays; the scale is retained."""
        for item in self._overlay:
            self._scene.removeItem(item)
        self._overlay = []
        self._pending = []
        self.status.emit(self._prompt())

    def _prompt(self) -> str:
        """Guidance text for the current mode and calibration state."""
        if self._sheet_id is None:
            return "Import sheets, then double-click one to open it."
        scale = self.calibration()
        suffix = (
            f"Scale: {scale.describe()}"
            if scale is not None
            else "Scale: NOT SET — calibrate before measuring."
        )
        if self._mode is ViewerMode.PAN:
            return f"Pan/zoom. {suffix}"
        if self._mode is ViewerMode.CALIBRATE:
            return (
                "Calibrate: click the two ends of a printed dimension, then "
                f"type its length. {suffix}"
            )
        if self._mode is ViewerMode.DISTANCE:
            return f"Measure length: click both ends of a wall. {suffix}"
        return (
            "Measure area: click each corner, then double-click to close "
            f"the shape. {suffix}"
        )

    # -- interaction ------------------------------------------------------

    def mousePressEvent(self, event: object) -> None:
        """Collect measurement points; pan normally in PAN mode."""
        if self._mode is ViewerMode.PAN or self._pixmap_item is None:
            super().mousePressEvent(event)  # type: ignore[arg-type]
            return

        button = event.button()  # type: ignore[attr-defined]
        if button == Qt.MouseButton.RightButton:
            self._pending = []
            self.status.emit("Measurement cancelled. " + self._prompt())
            return
        if button != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)  # type: ignore[arg-type]
            return

        scene_point = self.mapToScene(
            event.position().toPoint()  # type: ignore[attr-defined]
        )
        self._pending.append(
            Point(from_float(scene_point.x()), from_float(scene_point.y()))
        )

        if self._mode is ViewerMode.AREA:
            self.status.emit(
                f"{len(self._pending)} corner(s) marked; double-click to "
                "close the shape."
            )
            return
        if len(self._pending) == 2:
            start, end = self._pending
            self._pending = []
            if self._mode is ViewerMode.CALIBRATE:
                self._finish_calibration(start, end)
            else:
                self._finish_distance(start, end)
        else:
            self.status.emit("First point marked; click the second.")

    def mouseDoubleClickEvent(self, event: object) -> None:
        """Close a traced area."""
        if self._mode is not ViewerMode.AREA:
            super().mouseDoubleClickEvent(event)  # type: ignore[arg-type]
            return
        points = list(self._pending)
        self._pending = []
        if len(points) < 3:
            self.status.emit(
                "An area needs at least three corners. " + self._prompt()
            )
            return
        self._finish_area(points)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt API)
        """Zoom with the mouse wheel."""
        factor = (
            _ZOOM_IN_FACTOR
            if event.angleDelta().y() > 0
            else 1 / _ZOOM_IN_FACTOR
        )
        self.scale(factor, factor)

    # -- measurement completion -------------------------------------------

    def _finish_calibration(self, start: Point, end: Point) -> None:
        """Ask for the printed length of the drawn span and set the scale."""
        text, accepted = QInputDialog.getText(
            self,
            "Set drawing scale",
            "Printed length of the span you just drew\n"
            "(e.g. 20'-0\", 20' 6 1/2\", or 246 for inches):",
        )
        if not accepted:
            self.status.emit("Calibration cancelled. " + self._prompt())
            return
        try:
            known = parse_length_inches(text)
            scale = calibrate(start, end, known)
        except (LengthParseError, ScaleUncalibratedError) as exc:
            QMessageBox.warning(self, "Could not set scale", str(exc))
            return

        if self._sheet_id is not None:
            self._calibrations[self._sheet_id] = scale
        self._draw_span(start, end, format_inches(known), _CALIBRATION_COLOUR)
        self.calibrated.emit(scale.describe())
        self.status.emit(self._prompt())

    def _finish_distance(self, start: Point, end: Point) -> None:
        """Measure and publish a wall length."""
        try:
            inches = measure_length_inches(start, end, self.calibration())
        except ScaleUncalibratedError as exc:
            QMessageBox.warning(self, "No scale set", str(exc))
            return
        self._draw_span(start, end, format_inches(inches), _DISTANCE_COLOUR)
        self.distance_measured.emit(inches)
        self.status.emit(
            f"Measured {format_inches(inches)}. " + self._prompt()
        )

    def _finish_area(self, points: list[Point]) -> None:
        """Measure and publish a traced area."""
        try:
            area = measure_area_sf(points, self.calibration())
        except ScaleUncalibratedError as exc:
            QMessageBox.warning(self, "No scale set", str(exc))
            return
        self._draw_polygon(points, format_area_sf(area))
        self.area_measured.emit(area)
        self.status.emit(f"Measured {format_area_sf(area)}. " + self._prompt())

    # -- overlay drawing ---------------------------------------------------

    @staticmethod
    def _pen(colour: str) -> QPen:
        """A zoom-independent pen, so overlays stay legible at any zoom."""
        pen = QPen(QColor(colour))
        pen.setWidth(2)
        pen.setCosmetic(True)
        return pen

    def _draw_span(
        self, start: Point, end: Point, label: str, colour: str
    ) -> None:
        """Draw a measured or calibration span with its label."""
        line = self._scene.addLine(
            float(start.x),
            float(start.y),
            float(end.x),
            float(end.y),
            self._pen(colour),
        )
        self._overlay.append(line)
        midpoint = QPointF(
            float((start.x + end.x) / 2), float((start.y + end.y) / 2)
        )
        self._add_label(label, midpoint, colour)

    def _draw_polygon(self, points: list[Point], label: str) -> None:
        """Draw a traced area with its label."""
        polygon = QPolygonF(
            [QPointF(float(point.x), float(point.y)) for point in points]
        )
        fill = QColor(_AREA_COLOUR)
        fill.setAlpha(48)
        item = self._scene.addPolygon(
            polygon, self._pen(_AREA_COLOUR), QBrush(fill)
        )
        self._overlay.append(item)
        centre = polygon.boundingRect().center()
        self._add_label(label, centre, _AREA_COLOUR)

    def _add_label(self, text: str, at: QPointF, colour: str) -> None:
        """Place a label that stays screen-sized regardless of zoom."""
        item = self._scene.addSimpleText(text)
        item.setBrush(QBrush(QColor(colour)))
        item.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True
        )
        item.setPos(at)
        item.setZValue(10)
        self._overlay.append(item)
