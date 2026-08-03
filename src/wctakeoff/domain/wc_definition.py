"""WCDefinition and the SetReadRegistry.

Requirement ids: FR-2, NFR-1 (ADR-002).

The registry stores each WC definition verbatim as captured from the
schedule and exposes storage and retrieval ONLY. It contains no
arithmetic whatsoever: no derivation, no normalisation, no defaulting.
Any required-but-absent field is the UNKNOWN sentinel, never an imputed
value. Compute modules import this module; this module imports nothing
from any compute module (one-way dependency, ADR-002).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from wctakeoff.domain.ids import SheetId
from wctakeoff.domain.models import (
    MaybeUnknownDecimal,
    MaybeUnknownMatch,
    MaybeUnknownStr,
)
from wctakeoff.domain.units import UNKNOWN, UnitOfSale, V1_WC_TAGS


class WCDefinition(BaseModel):
    """A schedule row for one WC tag, captured verbatim (SET READ, FR-2)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    wc_tag: str = Field(min_length=1)
    manufacturer: MaybeUnknownStr = UNKNOWN
    pattern_name: MaybeUnknownStr = UNKNOWN
    roll_width_in: MaybeUnknownDecimal = UNKNOWN
    repeat_in: MaybeUnknownDecimal = UNKNOWN
    match_type: MaybeUnknownMatch = UNKNOWN
    unit_of_sale: UnitOfSale
    yield_per_unit: MaybeUnknownDecimal = UNKNOWN
    source_sheet_id: SheetId

    def unknown_fields(self) -> list[str]:
        """Names of SET READ fields currently UNKNOWN (for flagging, FR-8)."""
        out: list[str] = []
        for name in (
            "manufacturer",
            "pattern_name",
            "roll_width_in",
            "repeat_in",
            "match_type",
            "yield_per_unit",
        ):
            if getattr(self, name) is UNKNOWN:
                out.append(name)
        return out


class SetReadRegistry:
    """Verbatim store of WC definitions. Exposes no arithmetic at all."""

    def __init__(self) -> None:
        self._definitions: dict[str, WCDefinition] = {}

    def upsert_wc_definition(self, defn: WCDefinition) -> WCDefinition:
        """upsert_wc_definition(defn: WCDefinition) -> WCDefinition

        Stores verbatim; any required-but-absent field must already be the
        UNKNOWN sentinel, never imputed. Frozen interface UpsertWCDefinition
        (FR-2).
        """
        if defn.wc_tag not in V1_WC_TAGS:
            raise ValueError(
                f"wc_tag {defn.wc_tag!r} is out of scope for v1; "
                f"only {V1_WC_TAGS} are accepted (ARCH-A9)"
            )
        self._definitions[defn.wc_tag] = defn
        return defn

    def get_wc_definition(self, wc_tag: str) -> WCDefinition | None:
        """get_wc_definition(wc_tag: str) -> WCDefinition | None

        None means defined-but-missing; the caller must flag, not default.
        Frozen interface GetWCDefinition (FR-2).
        """
        return self._definitions.get(wc_tag)

    def all_definitions(self) -> list[WCDefinition]:
        """All stored definitions, for the set-read reference block (FR-7)."""
        return list(self._definitions.values())
