"""Set-read and dimension entry forms.

Requirement ids: FR-2, FR-3, FR-4, NFR-4 (ADR-002, ADR-004, ADR-011).

Estimator-typed schedule fields, dimensions, openings and tags, entered
against the displayed sheet through the ManualEntryAdapter (entry is
confirmation at source). A field left blank is submitted as UNKNOWN,
never defaulted. The forms contain no takeoff arithmetic.

Values measured on the drawing arrive here through apply_measured_length
and apply_measured_area: a measurement lands in a field the estimator can
see and edit, and only becomes part of the takeoff when they submit it.
That is what keeps pixel measurement a cross-check the estimator signs
off rather than a silent dimension source (ARCH-A2, ADR-011).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wctakeoff.domain.ids import SheetId
from wctakeoff.domain.models import FieldRef, SubjectRef
from wctakeoff.domain.units import UNKNOWN, MatchType, UnitOfSale, V1_WC_TAGS
from wctakeoff.extraction.manual import ManualEntryAdapter
from wctakeoff.ui.measure import (
    LengthParseError,
    format_inches,
    parse_length_inches,
)

#: Displayed precision for a value pushed in from the measuring tools.
_MEASURED_PLACES = Decimal("0.0001")

_NO_SHEET_TITLE = "No sheet selected"
_NO_SHEET_DETAIL = (
    "Every value is recorded against the sheet it was read from (NFR-1). "
    "Import sheets from the File menu, then double-click one in the "
    "Drawing Set panel before entering values."
)


class WCDefinitionForm(QWidget):
    """Verbatim schedule-row entry for one WC tag (FR-2, SET READ)."""

    #: Emitted after entered values have been queued on the adapter, so the
    #: shell can project them into the set-read registry and recompute
    #: (FR-2, AC-7.2 recompute loop).
    submitted = Signal()

    def __init__(self, adapter: ManualEntryAdapter) -> None:
        super().__init__()
        self._adapter = adapter
        self._current_sheet: SheetId | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Schedule fields are captured VERBATIM. Leave a field blank "
                "to record it as UNKNOWN — it will block quantities for "
                "that WC until resolved (never defaulted)."
            )
        )
        form = QFormLayout()
        self.tag_box = QComboBox()
        self.tag_box.addItems(list(V1_WC_TAGS))
        self.manufacturer = QLineEdit()
        self.pattern_name = QLineEdit()
        self.roll_width_in = QLineEdit()
        self.repeat_in = QLineEdit()
        self.match_type = QComboBox()
        self.match_type.addItems(["", *(m.value for m in MatchType)])
        self.unit_of_sale = QComboBox()
        self.unit_of_sale.addItems([u.value for u in UnitOfSale])
        self.yield_per_unit = QLineEdit()
        form.addRow("WC tag", self.tag_box)
        form.addRow("Manufacturer", self.manufacturer)
        form.addRow("Pattern name", self.pattern_name)
        form.addRow("Roll/bolt width (in)", self.roll_width_in)
        form.addRow("Pattern repeat (in)", self.repeat_in)
        form.addRow("Match type", self.match_type)
        form.addRow("Unit of sale", self.unit_of_sale)
        form.addRow("Yield per unit", self.yield_per_unit)
        layout.addLayout(form)
        self.submit = QPushButton("Record schedule row (verbatim)")
        self.submit.clicked.connect(self._on_submit)
        layout.addWidget(self.submit)
        layout.addStretch(1)

    def set_current_sheet(self, sheet_id: SheetId) -> None:
        """The sheet the estimator is reading from (provenance, NFR-1)."""
        self._current_sheet = sheet_id

    @staticmethod
    def _length_or_unknown(text: str) -> object:
        """A length in inches, or UNKNOWN — never a substituted default."""
        try:
            return parse_length_inches(text)
        except LengthParseError:
            return UNKNOWN

    @staticmethod
    def _decimal_or_unknown(text: str) -> object:
        text = text.strip()
        if not text:
            return UNKNOWN
        try:
            return Decimal(text)
        except InvalidOperation:
            return UNKNOWN

    def _on_submit(self) -> None:
        if self._current_sheet is None:
            QMessageBox.warning(self, _NO_SHEET_TITLE, _NO_SHEET_DETAIL)
            return
        wc_tag = self.tag_box.currentText()
        subject = SubjectRef(kind="wc_definition", ref_id=wc_tag)
        values: dict[str, object] = {
            "manufacturer": self.manufacturer.text().strip() or UNKNOWN,
            "pattern_name": self.pattern_name.text().strip() or UNKNOWN,
            "roll_width_in": self._length_or_unknown(self.roll_width_in.text()),
            "repeat_in": self._length_or_unknown(self.repeat_in.text()),
            "match_type": (
                MatchType(self.match_type.currentText())
                if self.match_type.currentText()
                else UNKNOWN
            ),
            "unit_of_sale": UnitOfSale(self.unit_of_sale.currentText()),
            "yield_per_unit": self._decimal_or_unknown(
                self.yield_per_unit.text()
            ),
        }
        for field_name, value in values.items():
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name=field_name),
                value,
            )
        self.submitted.emit()


class DimensionForm(QWidget):
    """Wall dimension, area and opening entry against a sheet (FR-4)."""

    #: Emitted after entered values have been queued on the adapter (FR-4).
    submitted = Signal()

    #: Where the next measurement taken on the drawing should land.
    WIDTH = "Wall width"
    HEIGHT = "Applied height"
    OPENING_WIDTH = "Opening width"
    OPENING_HEIGHT = "Opening height"
    _TARGETS = (WIDTH, HEIGHT, OPENING_WIDTH, OPENING_HEIGHT)

    def __init__(self, adapter: ManualEntryAdapter) -> None:
        super().__init__()
        self._adapter = adapter
        self._current_sheet: SheetId | None = None
        self._opening_counts: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Lengths accept feet-inches or plain inches: 20'-6\", "
                "20' 6 1/2\", or 246. Measurements taken on the drawing "
                "land in the field selected below for you to confirm."
            )
        )

        target_form = QFormLayout()
        self.measure_target = QComboBox()
        self.measure_target.addItems(list(self._TARGETS))
        target_form.addRow("Send next measurement to", self.measure_target)
        layout.addLayout(target_form)

        form = QFormLayout()
        self.room_number = QLineEdit()
        self.wall_designation = QLineEdit()
        self.width_in = QLineEdit()
        self.height_in = QLineEdit()
        self.measured_area_sf = QLineEdit()
        self.measured_area_sf.setPlaceholderText(
            "optional — traced area, for non-rectangular walls"
        )
        self.wc_tag = QComboBox()
        self.wc_tag.addItems(["", *V1_WC_TAGS])
        form.addRow("Room number", self.room_number)
        form.addRow("Wall designation", self.wall_designation)
        form.addRow("Width", self.width_in)
        form.addRow("Applied height", self.height_in)
        form.addRow("Measured wall area (sf)", self.measured_area_sf)
        form.addRow("WC tag (wall-level override)", self.wc_tag)
        layout.addLayout(form)

        self.submit = QPushButton("Record dimensions")
        self.submit.clicked.connect(self._on_submit)
        layout.addWidget(self.submit)

        openings_box = QGroupBox("Openings on this wall")
        openings_layout = QVBoxLayout(openings_box)
        opening_form = QFormLayout()
        self.opening_kind = QComboBox()
        self.opening_kind.addItems(["DOOR", "WINDOW", "OTHER"])
        self.opening_width_in = QLineEdit()
        self.opening_height_in = QLineEdit()
        opening_form.addRow("Type", self.opening_kind)
        opening_form.addRow("Width", self.opening_width_in)
        opening_form.addRow("Height", self.opening_height_in)
        openings_layout.addLayout(opening_form)
        self.add_opening = QPushButton("Add opening to this wall")
        self.add_opening.clicked.connect(self._on_add_opening)
        openings_layout.addWidget(self.add_opening)
        self.opening_list = QListWidget()
        openings_layout.addWidget(self.opening_list)
        layout.addWidget(openings_box)
        layout.addStretch(1)

    def set_current_sheet(self, sheet_id: SheetId) -> None:
        self._current_sheet = sheet_id

    # -- measurement intake ------------------------------------------------

    def apply_measured_length(self, inches: Decimal) -> None:
        """Place a measured length into the selected field.

        The target advances afterwards so an estimator can measure a wall's
        width and height back to back without touching the selector.
        """
        # Plain fixed-point, never Decimal.normalize(): normalize turns
        # 240.0000 into 2.4E+2, which the length parser rightly rejects.
        text = format(inches.quantize(_MEASURED_PLACES), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        target = self.measure_target.currentText()
        field = {
            self.WIDTH: self.width_in,
            self.HEIGHT: self.height_in,
            self.OPENING_WIDTH: self.opening_width_in,
            self.OPENING_HEIGHT: self.opening_height_in,
        }.get(target)
        if field is None:
            return
        field.setText(text)
        following = (self._TARGETS.index(target) + 1) % len(self._TARGETS)
        self.measure_target.setCurrentIndex(following)

    def apply_measured_area(self, square_feet: Decimal) -> None:
        """Place a traced area into the measured-area field."""
        self.measured_area_sf.setText(
            str(square_feet.quantize(Decimal("0.01")))
        )

    # -- entry -------------------------------------------------------------

    def _wall_reference(self) -> tuple[str, str] | None:
        """The (room, wall) pair, warning when either is missing."""
        room = self.room_number.text().strip()
        wall = self.wall_designation.text().strip()
        if not room or not wall:
            QMessageBox.warning(
                self,
                "Room and wall required",
                (
                    "A wall is identified by (room, wall) (ADR-009); both "
                    "must be entered before dimensions or openings can be "
                    "recorded."
                ),
            )
            return None
        return room, wall

    def _on_submit(self) -> None:
        if self._current_sheet is None:
            QMessageBox.warning(self, _NO_SHEET_TITLE, _NO_SHEET_DETAIL)
            return
        reference = self._wall_reference()
        if reference is None:
            return
        room, wall = reference
        subject = SubjectRef(kind="wall", ref_id=f"{room}/{wall}")

        for field_name, widget in (
            ("width_in", self.width_in),
            ("applied_height_in", self.height_in),
        ):
            text = widget.text().strip()
            if not text:
                continue  # a missing dimension stays missing → flag path
            try:
                value = parse_length_inches(text)
            except LengthParseError as exc:
                QMessageBox.warning(self, "Unreadable dimension", str(exc))
                return
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name=field_name),
                value,
            )

        area_text = self.measured_area_sf.text().strip()
        if area_text:
            try:
                area = Decimal(area_text)
            except InvalidOperation:
                QMessageBox.warning(
                    self,
                    "Unreadable area",
                    f"{area_text!r} is not a readable square-foot area.",
                )
                return
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name="manual_area_sf"),
                area,
            )

        tag = self.wc_tag.currentText()
        if tag:
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name="wc_tag"),
                tag,
            )
        self.submitted.emit()

    def _on_add_opening(self) -> None:
        """Record one opening against the current wall (FR-4)."""
        if self._current_sheet is None:
            QMessageBox.warning(self, _NO_SHEET_TITLE, _NO_SHEET_DETAIL)
            return
        reference = self._wall_reference()
        if reference is None:
            return
        room, wall = reference

        try:
            width = parse_length_inches(self.opening_width_in.text())
            height = parse_length_inches(self.opening_height_in.text())
        except LengthParseError as exc:
            QMessageBox.warning(self, "Unreadable opening", str(exc))
            return

        wall_key = f"{room}/{wall}"
        index = self._opening_counts.get(wall_key, 0) + 1
        self._opening_counts[wall_key] = index
        subject = SubjectRef(
            kind="opening", ref_id=f"{wall_key}/O{index}"
        )
        kind = self.opening_kind.currentText()
        for field_name, value in (
            ("kind", kind),
            ("width_in", width),
            ("height_in", height),
        ):
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name=field_name),
                value,
            )

        self.opening_list.addItem(
            f"{wall_key} · O{index} · {kind} · "
            f"{format_inches(width)} × {format_inches(height)}"
        )
        self.opening_width_in.clear()
        self.opening_height_in.clear()
        self.submitted.emit()
