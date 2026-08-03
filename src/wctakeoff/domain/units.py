"""Units, enumerations and the UNKNOWN sentinel.

Requirement ids: FR-2, FR-5, FR-8 (ADR-002, ADR-007, ADR-008).

The UNKNOWN sentinel encodes ADR-002: a schedule field the takeoff needs
but the schedule omits is stored as UNKNOWN, never defaulted and never
imputed. UNKNOWN is deliberately not a number: any attempt to use it in
arithmetic raises TypeError, which makes the set-read / compute boundary
mechanically un-crossable by an unknown value.

Per ADR-007 there is intentionally NO conversion function between
LINEAR_YARD and ROLL anywhere in this codebase.
"""
from __future__ import annotations

import enum
from typing import Any, Final, TypeAlias


class _UnknownType:
    """Singleton sentinel for a required-but-absent SET READ field (ADR-002)."""

    _instance: "_UnknownType | None" = None

    def __new__(cls) -> "_UnknownType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNKNOWN"

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _UnknownType)

    def __hash__(self) -> int:
        return hash("wctakeoff.UNKNOWN")

    def __reduce__(self) -> tuple[Any, ...]:
        return (_UnknownType, ())


UNKNOWN: Final[_UnknownType] = _UnknownType()

Unknown: TypeAlias = _UnknownType


def is_unknown(value: object) -> bool:
    """True when the value is the UNKNOWN sentinel."""
    return isinstance(value, _UnknownType)


class UnitOfSale(enum.Enum):
    """Per-WC unit of sale, read from that WC's own schedule row (ADR-007)."""

    LINEAR_YARD = "LINEAR_YARD"
    ROLL = "ROLL"


class MatchType(enum.Enum):
    """Pattern match type. UNKNOWN match raises a blocking flag (ARCH-A8)."""

    STRAIGHT = "STRAIGHT"
    HALF_DROP = "HALF_DROP"
    RANDOM = "RANDOM"


class SheetRole(enum.Enum):
    """Role of an ingested sheet (FR-1); UNASSIGNED raises a flag."""

    SCHEDULE = "SCHEDULE"
    FINISH_PLAN = "FINISH_PLAN"
    CEILING_HEIGHT_PLAN = "CEILING_HEIGHT_PLAN"
    ELEVATION = "ELEVATION"
    UNASSIGNED = "UNASSIGNED"


class TakeoffMethod(enum.Enum):
    """Quantity method selected per WC definition (FR-5)."""

    STRIP = "STRIP"
    AREA = "AREA"


class ExportFormat(enum.Enum):
    """Supported export formats (FR-7)."""

    XLSX = "XLSX"
    PDF = "PDF"


class FlagKind(enum.Enum):
    """Typed review-queue flag kinds (FR-8, ADR-005)."""

    UNKNOWN_SCHEDULE_FIELD = "UNKNOWN_SCHEDULE_FIELD"
    MISSING_HEIGHT = "MISSING_HEIGHT"
    UNRESOLVED_UNO = "UNRESOLVED_UNO"
    UNDEFINED_WC = "UNDEFINED_WC"
    UNUSED_WC = "UNUSED_WC"
    CONFLICT = "CONFLICT"
    UNREADABLE_DIMENSION = "UNREADABLE_DIMENSION"
    NON_RECTANGULAR = "NON_RECTANGULAR"
    UNKNOWN_MATCH_TYPE = "UNKNOWN_MATCH_TYPE"


class ApplicationOrigin(enum.Enum):
    """How an Application was resolved (ADR-008); wall override wins."""

    ROOM_BLANKET = "ROOM_BLANKET"
    WALL_OVERRIDE = "WALL_OVERRIDE"
    ELEVATION_TAG = "ELEVATION_TAG"


#: The only wallcovering tags in scope for v1 (ARCH-A9).
V1_WC_TAGS: Final[tuple[str, str, str]] = ("WC-1", "WC-2", "WC-3")
