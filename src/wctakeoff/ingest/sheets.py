"""SheetIngestService: PNG sheets into a role-tagged drawing set.

Requirement ids: FR-1 (AC-1.1, AC-1.2, AC-1.3).

Accepts PNG files, rejects non-PNG or unreadable files with a clear
reason (never an exception — rejects go into IngestResult.rejected),
generates thumbnails via Pillow, infers roles where possible and flags
every sheet left unlabelled.
"""
from __future__ import annotations

import io
from pathlib import Path
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
from wctakeoff.review.flags import FlagRegistry

_THUMBNAIL_SIZE = (256, 256)


class SheetIngestService:
    """Ingests PNG sheets and maintains their role assignments (FR-1)."""

    def __init__(self, flags: FlagRegistry | None = None) -> None:
        self._flags = flags
        self._sheets: dict[SheetId, Sheet] = {}

    def ingest_sheets(
        self, paths: Sequence[Path], set_id: SetId
    ) -> IngestResult:
        """ingest_sheets(paths, set_id) -> IngestResult

        Frozen interface IngestSheets (FR-1). Raises nothing; non-PNG or
        unreadable files are placed in rejected with a reason (AC-1.2).
        Unlabelled sheets are listed and flagged (AC-1.3).
        """
        accepted: list[Sheet] = []
        rejected: list[RejectedFile] = []
        unlabelled: list[SheetId] = []

        for path in paths:
            try:
                with Image.open(path) as image:
                    if (image.format or "").upper() != "PNG":
                        rejected.append(
                            RejectedFile(
                                path=path,
                                reason=(
                                    f"not a PNG (detected {image.format!r}); "
                                    "only PNG sheets are accepted"
                                ),
                            )
                        )
                        continue
                    thumbnail = self._thumbnail(image)
            except FileNotFoundError:
                rejected.append(
                    RejectedFile(path=path, reason="file not found")
                )
                continue
            except UnidentifiedImageError:
                rejected.append(
                    RejectedFile(
                        path=path,
                        reason="unreadable: not a decodable image file",
                    )
                )
                continue
            except OSError as exc:
                rejected.append(
                    RejectedFile(path=path, reason=f"unreadable: {exc}")
                )
                continue

            sheet_number = path.stem
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
                                f"sheet {path.name} has no role; assign "
                                "SCHEDULE, FINISH_PLAN, CEILING_HEIGHT_PLAN "
                                "or ELEVATION (AC-1.3)"
                            ),
                        )
                    )

        return IngestResult(
            accepted=accepted, rejected=rejected, unlabelled=unlabelled
        )

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
        buffer = io.BytesIO()
        copy.save(buffer, format="PNG")
        return buffer.getvalue()
