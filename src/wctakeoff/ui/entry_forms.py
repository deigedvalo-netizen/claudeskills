"""Set-read and dimension entry forms.

Requirement ids: FR-2, FR-3, FR-4, NFR-4 (ADR-002, ADR-004).

Estimator-typed schedule fields, dimensions and tags, entered against
the displayed sheet through the ManualEntryAdapter (entry is
confirmation at source). A field left blank is submitted as UNKNOWN,
never defaulted. The forms contain no takeoff arithmetic.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wctakeoff.domain.ids import SheetId
from wctakeoff.domain.models import FieldRef, SubjectRef
from wctakeoff.domain.units import UNKNOWN, MatchType, UnitOfSale, V1_WC_TAGS
from wctakeoff.extraction.manual import ManualEntryAdapter


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

    def set_current_sheet(self, sheet_id: SheetId) -> None:
        """The sheet the estimator is reading from (provenance, NFR-1)."""
        self._current_sheet = sheet_id

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
            QMessageBox.warning(
                self,
                "No sheet selected",
                (
                    "Every value is recorded against the sheet it was read "
                    "from (NFR-1). Import sheets from the File menu, then "
                    "double-click one in the Drawing Set panel before "
                    "entering schedule fields."
                ),
            )
            return
        wc_tag = self.tag_box.currentText()
        subject = SubjectRef(kind="wc_definition", ref_id=wc_tag)
        values: dict[str, object] = {
            "manufacturer": self.manufacturer.text().strip() or UNKNOWN,
            "pattern_name": self.pattern_name.text().strip() or UNKNOWN,
            "roll_width_in": self._decimal_or_unknown(self.roll_width_in.text()),
            "repeat_in": self._decimal_or_unknown(self.repeat_in.text()),
            "match_type": (
                MatchType(self.match_type.currentText())
                if self.match_type.currentText()
                else UNKNOWN
            ),
            "unit_of_sale": UnitOfSale(self.unit_of_sale.currentText()),
            "yield_per_unit": self._decimal_or_unknown(self.yield_per_unit.text()),
        }
        for field_name, value in values.items():
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name=field_name),
                value,
            )
        self.submitted.emit()


class DimensionForm(QWidget):
    """Wall dimension and opening entry against the displayed sheet (FR-4)."""

    #: Emitted after entered values have been queued on the adapter (FR-4).
    submitted = Signal()

    def __init__(self, adapter: ManualEntryAdapter) -> None:
        super().__init__()
        self._adapter = adapter
        self._current_sheet: SheetId | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.room_number = QLineEdit()
        self.wall_designation = QLineEdit()
        self.width_in = QLineEdit()
        self.height_in = QLineEdit()
        self.wc_tag = QComboBox()
        self.wc_tag.addItems(["", *V1_WC_TAGS])
        form.addRow("Room number", self.room_number)
        form.addRow("Wall designation", self.wall_designation)
        form.addRow("Width (in)", self.width_in)
        form.addRow("Applied height (in)", self.height_in)
        form.addRow("WC tag (wall-level override)", self.wc_tag)
        layout.addLayout(form)
        self.submit = QPushButton("Record dimensions")
        self.submit.clicked.connect(self._on_submit)
        layout.addWidget(self.submit)

    def set_current_sheet(self, sheet_id: SheetId) -> None:
        self._current_sheet = sheet_id

    def _on_submit(self) -> None:
        if self._current_sheet is None:
            QMessageBox.warning(
                self,
                "No sheet selected",
                (
                    "Dimensions are recorded against the sheet they were "
                    "read from (NFR-1). Import sheets from the File menu, "
                    "then double-click one in the Drawing Set panel before "
                    "entering dimensions."
                ),
            )
            return
        room = self.room_number.text().strip()
        wall = self.wall_designation.text().strip()
        if not room or not wall:
            QMessageBox.warning(
                self,
                "Room and wall required",
                (
                    "A wall is identified by (room, wall) (ADR-009); both "
                    "must be entered before dimensions can be recorded."
                ),
            )
            return
        subject = SubjectRef(kind="wall", ref_id=f"{room}/{wall}")
        for field_name, widget in (
            ("width_in", self.width_in),
            ("applied_height_in", self.height_in),
        ):
            text = widget.text().strip()
            if not text:
                continue  # a missing dimension stays missing → flag path
            try:
                value: object = Decimal(text)
            except InvalidOperation:
                continue
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name=field_name),
                value,
            )
        tag = self.wc_tag.currentText()
        if tag:
            self._adapter.enter_value(
                self._current_sheet,
                FieldRef(subject=subject, field_name="wc_tag"),
                tag,
            )
        self.submitted.emit()
