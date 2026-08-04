"""SheetIngestService: PDF and PNG sheets into a role-tagged drawing set.

Requirement ids: FR-1 (AC-1.1, AC-1.2).

Accepts PDF drawing sets and PNG sheets, rejects anything else or
unreadable with a clear reason (never an exception — rejects go into
IngestResult.rejected), generates thumbnails via Pillow, infers roles
where possible and flags every sheet left unlabelled.

Each page of a PDF becomes one Sheet. Pages are rasterised once at a
fixed resolution into a local render cache and the Sheet then points at
that PNG, so everything downstream — viewer, thumbnails, persistence —
keeps working on a single image format. Rasterising at a fixed, recorded
DPI also means a sheet's pixel geometry is stable across re-imports,
which is what makes an estimator's scale calibration reproducible.
"""
from __future__ import annotations

import hashlib
import io
import re
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Sequence

from PIL import Image, UnidentifiedImageError

from wctakeoff.domain.ids import SetId, SheetId, new_sheet_id
from wctakeoff.domain.models import (
    Flag,
    IngestResult,
    RejectedFile,
    Sheet,
    SubjectRef,
)
from wctakeoff.domain.units import FlagKind, SheetRole
from wctakeoff.ingest.roles import infer_role
from wctakeoff.ingest.scale import DetectedScale, detect_page_scale
from wctakeoff.review.flags import FlagRegistry

_THUMBNAIL_SIZE = (256, 256)

#: Rasterisation resolution for PDF pages. Fixed rather than adaptive so
#: that re-importing the same PDF yields identical pixel geometry and a
#: previously established scale calibration still holds.
PDF_RENDER_DPI = 200

#: pypdfium2 expresses render scale relative to PDF user space (72/inch).
_PDF_POINTS_PER_INCH = 72


def render_cache_dir() -> Path:
    """Where rasterised PDF pages are cached, created on demand."""
    directory = Path.home() / ".wctakeoff" / "sheets"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _pdfium() -> ModuleType | None:
    """The PDF rasteriser, or None when it is unavailable.

    Imported lazily and defensively so that a missing renderer degrades
    to a clear per-file rejection (AC-1.2) instead of preventing the
    application from starting at all.
    """
    try:
        import pypdfium2
    except Exception:  # pragma: no cover - depends on the install
        return None
    return pypdfium2


class SheetIngestService:
    """Ingests PDF and PNG sheets and maintains role assignments (FR-1)."""

    def __init__(self, flags: FlagRegistry | None = None) -> None:
        self._flags = flags
        self._sheets: dict[SheetId, Sheet] = {}
        self._detected_scales: dict[SheetId, DetectedScale] = {}

    def ingest_sheets(
        self, paths: Sequence[Path], set_id: SetId
    ) -> IngestResult:
        """ingest_sheets(paths, set_id) -> IngestResult

        Frozen interface IngestSheets (FR-1). Raises nothing; unsupported
        or unreadable files are placed in rejected with a reason
        (AC-1.2). Unlabelled sheets are listed and flagged (AC-1.1).
        Every page of a PDF is ingested as its own sheet.
        """
        accepted: list[Sheet] = []
        rejected: list[RejectedFile] = []
        unlabelled: list[SheetId] = []

        for path in paths:
            if path.suffix.lower() == ".pdf":
                self._ingest_pdf(path, accepted, rejected, unlabelled)
            else:
                self._ingest_png(path, accepted, rejected, unlabelled)

        return IngestResult(
            accepted=accepted, rejected=rejected, unlabelled=unlabelled
        )

    # -- per-format ingest -----------------------------------------------

    def _ingest_png(
        self,
        path: Path,
        accepted: list[Sheet],
        rejected: list[RejectedFile],
        unlabelled: list[SheetId],
    ) -> None:
        """Ingest one PNG file, rejecting any other image format."""
        try:
            with Image.open(path) as image:
                if (image.format or "").upper() != "PNG":
                    rejected.append(
                        RejectedFile(
                            path=path,
                            reason=(
                                f"not a PDF or PNG (detected "
                                f"{image.format!r}); only PDF drawing sets "
                                "and PNG sheets are accepted"
                            ),
                        )
                    )
                    return
                thumbnail = self._thumbnail(image)
        except FileNotFoundError:
            rejected.append(RejectedFile(path=path, reason="file not found"))
            return
        except UnidentifiedImageError:
            rejected.append(
                RejectedFile(
                    path=path,
                    reason=(
                        "unreadable: not a decodable PDF or image file"
                    ),
                )
            )
            return
        except OSError as exc:
            rejected.append(
                RejectedFile(path=path, reason=f"unreadable: {exc}")
            )
            return

        self._register(path, path.stem, thumbnail, accepted, unlabelled)

    def _ingest_pdf(
        self,
        path: Path,
        accepted: list[Sheet],
        rejected: list[RejectedFile],
        unlabelled: list[SheetId],
    ) -> None:
        """Rasterise every page of a PDF into the render cache."""
        if not path.exists():
            rejected.append(RejectedFile(path=path, reason="file not found"))
            return

        pdfium = _pdfium()
        if pdfium is None:
            rejected.append(
                RejectedFile(
                    path=path,
                    reason=(
                        "PDF support is unavailable: the pypdfium2 renderer "
                        "is not installed in this environment"
                    ),
                )
            )
            return

        try:
            document = pdfium.PdfDocument(path)
        except Exception as exc:
            rejected.append(
                RejectedFile(
                    path=path,
                    reason=f"unreadable PDF: {exc}",
                )
            )
            return

        try:
            page_count = len(document)
            if page_count == 0:
                rejected.append(
                    RejectedFile(path=path, reason="PDF has no pages")
                )
                return
            for index in range(page_count):
                try:
                    self._ingest_pdf_page(
                        path, document, index, accepted, unlabelled
                    )
                except Exception as exc:
                    rejected.append(
                        RejectedFile(
                            path=path,
                            reason=(
                                f"page {index + 1} could not be rendered: "
                                f"{exc}"
                            ),
                        )
                    )
        finally:
            close = getattr(document, "close", None)
            if callable(close):
                close()

    def _ingest_pdf_page(
        self,
        source: Path,
        document: object,
        index: int,
        accepted: list[Sheet],
        unlabelled: list[SheetId],
    ) -> None:
        """Rasterise one PDF page, register it, and read its scale note."""
        page = document[index]  # type: ignore[index]
        destination = self._render_path(source, index)
        page_text = self._page_text(page)

        if destination.exists():
            with Image.open(destination) as cached:
                cached.load()
                thumbnail = self._thumbnail(cached)
                rendered_width = cached.width
        else:
            scale = PDF_RENDER_DPI / _PDF_POINTS_PER_INCH
            image = page.render(scale=scale).to_pil()
            try:
                image.save(destination, format="PNG")
                thumbnail = self._thumbnail(image)
                rendered_width = image.width
            finally:
                image.close()

        sheet_number = self._page_sheet_number(page_text, source, index)
        sheet = self._register(
            destination, sheet_number, thumbnail, accepted, unlabelled
        )

        detected = self._detect_scale(page, page_text, rendered_width)
        if detected is not None:
            self._detected_scales[sheet.sheet_id] = detected

    @staticmethod
    def _detect_scale(
        page: object, page_text: str, rendered_width: int
    ) -> DetectedScale | None:
        """Read the page's printed scale note against its true geometry.

        Returns None whenever the page does not state exactly one usable
        scale; the estimator then calibrates by hand rather than measuring
        against an assumed conversion (ADR-005).
        """
        try:
            width_points, _height = page.get_size()  # type: ignore[attr-defined]
        except Exception:
            return None
        try:
            page_width = Decimal(str(width_points))
        except Exception:
            return None
        return detect_page_scale(
            page_text, page_width, Decimal(rendered_width)
        )

    def detected_scale_for(self, sheet_id: SheetId) -> DetectedScale | None:
        """The scale read off this sheet's own title block, if any.

        Advisory only: it pre-fills the viewer, and an estimator's manual
        calibration always overrides it (ARCH-A2, ADR-011).
        """
        return self._detected_scales.get(sheet_id)

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _render_path(source: Path, index: int) -> Path:
        """Deterministic cache path for one rasterised page.

        Keyed on the absolute source path so two different PDFs sharing a
        file name cannot overwrite one another's pages, and on the DPI so
        a resolution change produces a distinct file rather than silently
        invalidating an existing calibration.
        """
        digest = hashlib.sha256(
            str(source.resolve()).encode("utf-8")
        ).hexdigest()[:12]
        name = f"{source.stem}-{digest}-p{index + 1}@{PDF_RENDER_DPI}.png"
        return render_cache_dir() / name

    @staticmethod
    def _page_text(page: object) -> str:
        """All extractable text on a page; empty for a scanned image page."""
        try:
            textpage = page.get_textpage()  # type: ignore[attr-defined]
            try:
                return textpage.get_text_range() or ""
            finally:
                close = getattr(textpage, "close", None)
                if callable(close):
                    close()
        except Exception:
            return ""

    @staticmethod
    def _page_sheet_number(text: str, source: Path, index: int) -> str:
        """Best-effort sheet number for a PDF page.

        Falls back to a positional label when the page carries no
        recognisable drawing number; an unrecognised label simply infers
        no role, and the sheet is then flagged for the estimator rather
        than being given a guessed one (ADR-005).
        """
        fallback = f"{source.stem}-p{index + 1}"
        matches = re.findall(r"\b[A-Z]{1,2}-?\d{2,3}(?:\.\d+)?\b", text or "")
        if not matches:
            return fallback
        # Title blocks sit late in a page's text stream, so the last
        # drawing-number-shaped token is the best available candidate.
        return f"{matches[-1]} ({fallback})"

    def _register(
        self,
        path: Path,
        sheet_number: str,
        thumbnail: bytes,
        accepted: list[Sheet],
        unlabelled: list[SheetId],
    ) -> Sheet:
        """Record an accepted sheet and flag it when its role is unclear."""
        role = infer_role(sheet_number)
        sheet = Sheet(
            sheet_id=new_sheet_id(),
            path=path,
            role=role,
            sheet_number=sheet_number,
            thumbnail=thumbnail,
        )
        self._sheets[sheet.sheet_id] = sheet
        accepted.append(sheet)

        if role is SheetRole.UNASSIGNED:
            unlabelled.append(sheet.sheet_id)
            if self._flags is not None:
                self._flags.raise_flag(
                    Flag(
                        kind=FlagKind.UNRESOLVED_UNO,
                        subject_ref=SubjectRef(
                            kind="sheet", ref_id=str(sheet.sheet_id)
                        ),
                        source_sheet_id=sheet.sheet_id,
                        blocks=[],
                        detail=(
                            f"sheet {sheet_number} has no role; assign "
                            "SCHEDULE, FINISH_PLAN, CEILING_HEIGHT_PLAN "
                            "or ELEVATION (AC-1.1)"
                        ),
                    )
                )
        return sheet

    def assign_sheet_role(self, sheet_id: SheetId, role: SheetRole) -> Sheet:
        """assign_sheet_role(sheet_id, role) -> Sheet

        Frozen interface AssignSheetRole (FR-1). The estimator's explicit
        assignment replaces any inferred role.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            raise KeyError(f"unknown sheet_id {sheet_id!r}")
        updated = sheet.model_copy(update={"role": role})
        self._sheets[sheet_id] = updated
        return updated

    def get_sheet(self, sheet_id: SheetId) -> Sheet | None:
        """Look up one ingested sheet."""
        return self._sheets.get(sheet_id)

    def all_sheets(self) -> list[Sheet]:
        """All ingested sheets for persistence and display."""
        return list(self._sheets.values())

    @staticmethod
    def _thumbnail(image: Image.Image) -> bytes:
        """Generate the ingest thumbnail (AC-1.1) as PNG bytes."""
        copy = image.copy()
        copy.thumbnail(_THUMBNAIL_SIZE)
        if copy.mode not in ("RGB", "RGBA", "L"):
            copy = copy.convert("RGB")
        buffer = io.BytesIO()
        copy.save(buffer, format="PNG")
        return buffer.getvalue()
