"""DesktopShell: the application window.

Requirement ids: FR-1, FR-7 (ADR-001, ADR-011).

Sheet import and role assignment, zoomable sheet viewer, set-read entry
forms, dimension entry, policy panel, docked review queue and the
takeoff view — wired over TakeoffPresenter and ManualEntryAdapter.
Contains no takeoff arithmetic (ADR-001 layering).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QTabWidget,
)

from wctakeoff.domain.ids import SetId, SheetId
from wctakeoff.domain.units import ExportFormat
from wctakeoff.extraction.manual import ManualEntryAdapter
from wctakeoff.ingest.sheets import SheetIngestService
from wctakeoff.policy.settings import PolicyStore
from wctakeoff.presentation.presenter import (
    ExportService,
    NotFinalisableError,
    TakeoffPresenter,
)
from wctakeoff.review.flags import FlagRegistry
from wctakeoff.review.gate import ConfirmationGate
from wctakeoff.ui.entry_forms import DimensionForm, WCDefinitionForm
from wctakeoff.ui.policy_panel import PolicyPanel
from wctakeoff.ui.review_panel import ReviewPanel
from wctakeoff.ui.sheet_viewer import SheetViewer
from wctakeoff.ui.takeoff_view import TakeoffViewWidget


class DesktopShell(QMainWindow):
    """The single-window desktop application (ADR-001)."""

    def __init__(
        self,
        set_id: SetId,
        ingest: SheetIngestService,
        adapter: ManualEntryAdapter,
        presenter: TakeoffPresenter,
        policy_store: PolicyStore,
        flags: FlagRegistry,
        gate: ConfirmationGate,
        export_service: ExportService,
        on_entry_committed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._set_id = set_id
        self._ingest = ingest
        self._presenter = presenter
        self._gate = gate
        self._export_service = export_service
        # Projection hook supplied by the composition root: turns queued
        # adapter proposals into registry/repository state before the read
        # model is rebuilt (ADR-004 step 3 of the data flow).
        self._on_entry_committed = on_entry_committed

        self.setWindowTitle("Wallcovering Takeoff")
        self.resize(1400, 900)

        # Central: sheet viewer + entry tabs + takeoff view.
        self._viewer = SheetViewer()
        self._wc_form = WCDefinitionForm(adapter)
        self._dim_form = DimensionForm(adapter)
        self._wc_form.submitted.connect(self._on_entry_submitted)
        self._dim_form.submitted.connect(self._on_entry_submitted)
        self._takeoff_widget = TakeoffViewWidget()
        tabs = QTabWidget()
        tabs.addTab(self._viewer, "Sheets")
        tabs.addTab(self._wc_form, "Schedule (SET READ)")
        tabs.addTab(self._dim_form, "Dimensions")
        tabs.addTab(self._takeoff_widget, "Takeoff")
        self.setCentralWidget(tabs)

        # Left dock: sheet list with roles.
        self._sheet_list = QListWidget()
        self._sheet_list.itemActivated.connect(self._on_sheet_activated)
        sheet_dock = QDockWidget("Drawing Set", self)
        sheet_dock.setWidget(self._sheet_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, sheet_dock)

        # Right docks: review queue (live, FR-8) and policy (ADR-010).
        self._review_panel = ReviewPanel(flags)
        review_dock = QDockWidget("Review Queue", self)
        review_dock.setWidget(self._review_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, review_dock)

        self._policy_panel = PolicyPanel(
            policy_store, set_id, on_changed=self.recompute
        )
        policy_dock = QDockWidget("Takeoff Policy", self)
        policy_dock.setWidget(self._policy_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, policy_dock)

        self._build_menu()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        import_action = file_menu.addAction("&Import PNG sheets…")
        import_action.triggered.connect(self._on_import)
        export_xlsx = file_menu.addAction("Export &XLSX…")
        export_xlsx.triggered.connect(
            lambda: self._on_export(ExportFormat.XLSX, "*.xlsx")
        )
        export_pdf = file_menu.addAction("Export &PDF…")
        export_pdf.triggered.connect(
            lambda: self._on_export(ExportFormat.PDF, "*.pdf")
        )

    def _on_import(self) -> None:
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self, "Import PNG sheets", "", "PNG sheets (*.png)"
        )
        if not paths:
            return
        result = self._ingest.ingest_sheets(
            [Path(p) for p in paths], self._set_id
        )
        for rejected in result.rejected:
            QMessageBox.warning(
                self,
                "Sheet rejected",
                f"{rejected.path.name}: {rejected.reason}",
            )
        self._refresh_sheet_list()
        self._review_panel.refresh()

    def _refresh_sheet_list(self) -> None:
        self._sheet_list.clear()
        for sheet in self._ingest.all_sheets():
            item = QListWidgetItem(
                f"{sheet.sheet_number or sheet.path.name} [{sheet.role.value}]"
            )
            item.setData(Qt.ItemDataRole.UserRole, str(sheet.sheet_id))
            self._sheet_list.addItem(item)

    def _on_sheet_activated(self, item: QListWidgetItem) -> None:
        sheet_id = SheetId(item.data(Qt.ItemDataRole.UserRole))
        sheet = self._ingest.get_sheet(sheet_id)
        if sheet is None:
            return
        self._viewer.show_sheet(sheet)
        self._wc_form.set_current_sheet(sheet_id)
        self._dim_form.set_current_sheet(sheet_id)

    def _on_entry_submitted(self) -> None:
        """Project newly entered values, then rebuild the read model.

        Entry alone only queues proposals on the extraction adapter; the
        composition root's hook is what promotes them through the
        confirmation gate into the set-read registry and the repository
        (FR-2, FR-3, FR-4, NFR-4). Without it the takeoff view would stay
        empty no matter what the estimator types.
        """
        if self._on_entry_committed is not None:
            self._on_entry_committed()
        self.recompute()

    def recompute(self) -> None:
        """Rebuild the read-model after any edit (AC-7.2 recompute loop)."""
        view = self._presenter.build_takeoff_view(self._set_id)
        self._takeoff_widget.show_view(view)
        self._review_panel.refresh()

    def _on_export(self, fmt: ExportFormat, pattern: str) -> None:
        status = self._gate.is_takeoff_finalisable(self._set_id)
        if not status.finalisable:
            QMessageBox.warning(
                self,
                "Not finalisable",
                (
                    f"{len(status.unconfirmed)} unconfirmed value(s) and "
                    f"{len(status.blocking)} blocking flag(s) remain; the "
                    "takeoff cannot be finalised (NFR-4)."
                ),
            )
            return
        dest, _selected_filter = QFileDialog.getSaveFileName(
            self, "Export takeoff", "", pattern
        )
        if not dest:
            return
        view = self._presenter.build_takeoff_view(self._set_id)
        try:
            written = self._export_service.export_takeoff(
                view, fmt, Path(dest)
            )
        except NotFinalisableError as exc:
            QMessageBox.warning(self, "Not finalisable", str(exc))
            return
        QMessageBox.information(self, "Exported", f"Written to {written}")
