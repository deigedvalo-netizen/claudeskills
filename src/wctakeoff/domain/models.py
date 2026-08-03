"""Domain entities for the wallcovering takeoff, as validated Pydantic models.

Requirement ids: FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-8, NFR-1, NFR-2, NFR-4.

These are the entities named in the architecture spec's data_model section.
Models are immutable (frozen) so a computed result can never be silently
mutated after the fact; recomputation replaces values, honouring NFR-2.
The SET READ versus COMPUTED distinction (ADR-002) is encoded in types:
SET READ fields admit the UNKNOWN sentinel; computed fields never do.
"""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wctakeoff.domain.ids import (
    ApplicationId,
    FlagId,
    OpeningId,
    RoomId,
    SetId,
    SheetId,
    ValueId,
    WallId,
)
from wctakeoff.domain.units import (
    ApplicationOrigin,
    FlagKind,
    MatchType,
    SheetRole,
    TakeoffMethod,
    UnitOfSale,
    Unknown,
    UnitOfSale as _UnitOfSale,  # noqa: F401  (re-export convenience)
)

_MODEL_CONFIG = ConfigDict(frozen=True, arbitrary_types_allowed=True)


class Sheet(BaseModel):
    """A role-tagged PNG sheet in the drawing set (FR-1)."""

    model_config = _MODEL_CONFIG

    sheet_id: SheetId
    path: Path
    role: SheetRole = SheetRole.UNASSIGNED
    sheet_number: str | None = None
    thumbnail: bytes = b""


class RejectedFile(BaseModel):
    """A file refused at ingest with the reason (AC-1.2)."""

    model_config = _MODEL_CONFIG

    path: Path
    reason: str


class IngestResult(BaseModel):
    """Outcome of ingest_sheets (FR-1): accepted, rejected, unlabelled."""

    model_config = _MODEL_CONFIG

    accepted: list[Sheet] = Field(default_factory=list)
    rejected: list[RejectedFile] = Field(default_factory=list)
    unlabelled: list[SheetId] = Field(default_factory=list)


class DrawingSet(BaseModel):
    """One project's set of sheets (ARCH-A10: one run, one set)."""

    model_config = _MODEL_CONFIG

    set_id: SetId
    project_name: str = Field(min_length=1)
    sheets: list[Sheet] = Field(min_length=1)
    created_at: _dt.datetime

    @field_validator("created_at")
    @classmethod
    def _utc_only(cls, v: _dt.datetime) -> _dt.datetime:
        if v.tzinfo is None or v.utcoffset() != _dt.timedelta(0):
            raise ValueError("created_at must be timezone-aware UTC")
        return v


class Opening(BaseModel):
    """A door/window/etc. opening in a wall (FR-4)."""

    model_config = _MODEL_CONFIG

    opening_id: OpeningId
    kind: str = "OTHER"
    width_in: Decimal = Field(gt=0)
    height_in: Decimal = Field(gt=0)

    @property
    def area_sf(self) -> Decimal:
        """Derived opening area in square feet, compared to the policy threshold."""
        return (self.width_in * self.height_in) / Decimal(144)


class Wall(BaseModel):
    """A wall with (room_id, wall_id) de-duplication identity (ADR-009)."""

    model_config = _MODEL_CONFIG

    wall_id: WallId
    room_id: RoomId
    orientation: str = ""
    width_in: Decimal | None = None
    applied_height_in: Decimal | None = None
    openings: list[Opening] = Field(default_factory=list)
    manual_area_sf: Decimal | None = None


class Room(BaseModel):
    """A room as an explicit wall set (ADR-008); no height defaults ever."""

    model_config = _MODEL_CONFIG

    room_id: RoomId
    room_number: str = Field(min_length=1)
    ceiling_height_in: Decimal | None = None
    walls: list[Wall] = Field(default_factory=list)
    blanket_note: str | None = None


class Application(BaseModel):
    """A WC tag resolved onto one wall of one room (FR-3)."""

    model_config = _MODEL_CONFIG

    application_id: ApplicationId
    wc_tag: str = Field(min_length=1)
    room_id: RoomId
    wall_id: WallId
    origin: ApplicationOrigin
    source_sheet_id: SheetId


class SubjectRef(BaseModel):
    """What a flag or confirmation is about: entity kind plus its id."""

    model_config = _MODEL_CONFIG

    kind: str = Field(min_length=1)
    ref_id: str = Field(min_length=1)


class FieldRef(BaseModel):
    """A specific field of a specific entity, for proposals/confirmations."""

    model_config = _MODEL_CONFIG

    subject: SubjectRef
    field_name: str = Field(min_length=1)


class SourceRef(BaseModel):
    """Provenance for one input: the sheet and how it was read (NFR-1)."""

    model_config = _MODEL_CONFIG

    sheet_id: SheetId | None = None
    read_method: str = Field(min_length=1)


class Flag(BaseModel):
    """A review-queue entry (FR-8, ADR-005): flag rather than guess."""

    model_config = _MODEL_CONFIG

    flag_id: FlagId | None = None
    kind: FlagKind
    subject_ref: SubjectRef
    source_sheet_id: SheetId | None = None
    blocks: list[str] = Field(default_factory=list)
    detail: str = Field(min_length=1)


class PolicySnapshot(BaseModel):
    """Explicit takeoff configuration captured per result (ADR-010)."""

    model_config = _MODEL_CONFIG

    waste_pct: Decimal = Decimal("0.10")
    per_wc_waste: Mapping[str, Decimal] = Field(default_factory=dict)
    deduct_openings: bool = True
    opening_threshold_sf: Decimal = Decimal("20")
    trim_allowance_in: Decimal = Decimal("0")

    def waste_for(self, wc_tag: str) -> Decimal:
        """Per-WC override if present, else the global waste percentage."""
        return self.per_wc_waste.get(wc_tag, self.waste_pct)


class OpeningPolicy(BaseModel):
    """The opening-deduction slice of policy consumed by geometry (FR-4)."""

    model_config = _MODEL_CONFIG

    deduct_openings: bool = True
    opening_threshold_sf: Decimal = Decimal("20")


class WastePolicy(BaseModel):
    """The waste/trim slice of policy consumed by the math core (FR-5)."""

    model_config = _MODEL_CONFIG

    waste_pct: Decimal = Decimal("0.10")
    per_wc_waste: Mapping[str, Decimal] = Field(default_factory=dict)
    trim_allowance_in: Decimal = Decimal("0")

    def waste_for(self, wc_tag: str) -> Decimal:
        return self.per_wc_waste.get(wc_tag, self.waste_pct)


class AreaResult(BaseModel):
    """Gross/net wall area with every deduction itemised (FR-4, AC-4.x)."""

    model_config = _MODEL_CONFIG

    gross_sf: Decimal
    net_sf: Decimal
    deducted: list[Opening] = Field(default_factory=list)
    skipped: list[Opening] = Field(default_factory=list)


class QuantityResult(BaseModel):
    """Per-application computed quantity (FR-5); raw and with-waste distinct.

    application_id is attached by the calling service after the pure math
    functions return; the frozen compute_quantity_* signatures do not
    receive an application identity (see implementation manifest note).
    """

    model_config = _MODEL_CONFIG

    application_id: ApplicationId | None = None
    method: TakeoffMethod
    drops: int | None = None
    cut_length_in: Decimal | None = None
    net_area_sf: Decimal
    raw_qty: Decimal
    with_waste_qty: Decimal
    unit: UnitOfSale


class TakeoffLine(BaseModel):
    """One order line per WC in that WC's own unit (FR-6, ADR-007)."""

    model_config = _MODEL_CONFIG

    wc_tag: str = Field(min_length=1)
    contributing: list[ApplicationId] = Field(default_factory=list)
    raw_qty: Decimal = Decimal(0)
    with_waste_qty: Decimal = Decimal(0)
    order_qty: Decimal = Decimal(0)
    unit: UnitOfSale
    blocked_by: list[FlagId] = Field(default_factory=list)


class TraceRecord(BaseModel):
    """Formula + inputs + sources behind one displayed number (NFR-1)."""

    model_config = _MODEL_CONFIG

    value_id: ValueId
    formula: str = Field(min_length=1)
    inputs: Mapping[str, Decimal] = Field(default_factory=dict)
    sources: list[SourceRef] = Field(default_factory=list)


class Proposal(BaseModel):
    """A provisional read value from an extraction adapter (NFR-4)."""

    model_config = _MODEL_CONFIG

    field_ref: FieldRef
    value: object = None
    source_sheet_id: SheetId
    confidence: Decimal = Field(ge=0, le=1)
    confirmed: bool = False


class ConfirmedValue(BaseModel):
    """A value an estimator has confirmed; the only kind the engine accepts."""

    model_config = _MODEL_CONFIG

    field_ref: FieldRef
    value: object = None
    confirmed_by: str = Field(min_length=1)
    confirmed_at: _dt.datetime


class FinalisationStatus(BaseModel):
    """is_takeoff_finalisable answer (NFR-4, ADR-011)."""

    model_config = _MODEL_CONFIG

    finalisable: bool
    unconfirmed: list[FieldRef] = Field(default_factory=list)
    blocking: list[FlagId] = Field(default_factory=list)


class RoomNote(BaseModel):
    """A room-level blanket finish note as read from a plan (FR-3)."""

    model_config = _MODEL_CONFIG

    room_id: RoomId
    text: str = Field(min_length=1)
    source_sheet_id: SheetId


class WallTag(BaseModel):
    """A wall-level WC tag as read from a plan or elevation (FR-3)."""

    model_config = _MODEL_CONFIG

    room_id: RoomId
    wall_id: WallId
    wc_tag: str = Field(min_length=1)
    source_sheet_id: SheetId
    from_elevation: bool = False


class ApplicationResolution(BaseModel):
    """resolve_applications outcome: applications plus ambiguity flags."""

    model_config = _MODEL_CONFIG

    applications: list[Application] = Field(default_factory=list)
    ambiguous: list[Flag] = Field(default_factory=list)


#: A SET READ scalar that may be UNKNOWN (ADR-002).
MaybeUnknownDecimal = Union[Decimal, Unknown]
MaybeUnknownStr = Union[str, Unknown]
MaybeUnknownMatch = Union[MatchType, Unknown]
