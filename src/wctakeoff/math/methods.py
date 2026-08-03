"""Pure strip and area takeoff methods.

Requirement ids: FR-5, FR-6, NFR-2 (ADR-003, ADR-006, ADR-007).

Strip method (vertical repeat present):
    drops      = ceil(width / roll_width)
    cut_length = ceil((height + trim_allow) / repeat) * repeat
    total      = drops * cut_length
    raw_ly     = total / 36          # repeat loss already included
    with_waste = raw_ly * (1 + waste)  # waste applied exactly once

Area method (no repeat, or random match):
    net_sy     = net_area_sf / 9
    order_sy   = net_sy * (1 + waste)
    units      = ceil(order_sy / coverage_per_unit_sy)  # at aggregation

Waste is applied exactly once, after repeat loss, and raw and with-waste
figures are both retained (ADR-006). Units are never converted (ADR-007).
"""
from __future__ import annotations

from decimal import Decimal, localcontext

from wctakeoff.domain.models import QuantityResult, WastePolicy
from wctakeoff.domain.units import UNKNOWN, MatchType, TakeoffMethod
from wctakeoff.domain.wc_definition import WCDefinition
from wctakeoff.math.rounding import (
    DECIMAL_CONTEXT,
    ceil_div,
    ceil_to_multiple,
    exact,
)

_IN_PER_LY = Decimal(36)
_SF_PER_SY = Decimal(9)


class BlockedInputError(ValueError):
    """A required SET READ field is UNKNOWN; computation is blocked.

    The confirmation gate and flag registry prevent this path being
    reached (ADR-005, ADR-011); reaching it anyway is a defect upstream,
    never a cue to default.
    """


def _require_decimal(defn: WCDefinition, field: str) -> Decimal:
    value = getattr(defn, field)
    if value is UNKNOWN or not isinstance(value, Decimal):
        raise BlockedInputError(
            f"{defn.wc_tag}.{field} is UNKNOWN; quantity is blocked "
            "(FR-8, ADR-002) — flag, never default"
        )
    return value


def select_takeoff_method(defn: WCDefinition) -> TakeoffMethod:
    """select_takeoff_method(defn: WCDefinition) -> TakeoffMethod

    Frozen interface SelectTakeoffMethod (FR-5): STRIP when
    defn.repeat_in > 0, AREA when repeat_in == 0 or match type is RANDOM.
    An UNKNOWN repeat blocks selection rather than defaulting (ARCH-A8).
    """
    if defn.match_type is not UNKNOWN and defn.match_type == MatchType.RANDOM:
        return TakeoffMethod.AREA
    repeat = _require_decimal(defn, "repeat_in")
    if repeat > 0:
        return TakeoffMethod.STRIP
    return TakeoffMethod.AREA


def compute_quantity_strip(
    wall_width_in: Decimal,
    wall_height_in: Decimal,
    defn: WCDefinition,
    policy: WastePolicy,
) -> QuantityResult:
    """compute_quantity_strip(wall_width_in, wall_height_in, defn, policy)

    Frozen interface ComputeQuantityStrip (FR-5, ADR-006):
    drops = ceil(width/roll_width); cut_length = ceil((height +
    trim_allow)/repeat) * repeat; total = drops * cut_length;
    raw_ly = total/36; waste applied once.
    """
    roll_width = _require_decimal(defn, "roll_width_in")
    repeat = _require_decimal(defn, "repeat_in")
    if repeat <= 0:
        raise BlockedInputError(
            f"{defn.wc_tag}.repeat_in must be > 0 for the strip method; "
            "select_takeoff_method routes repeat==0 to AREA"
        )
    width = exact(wall_width_in)
    height = exact(wall_height_in)
    with localcontext(DECIMAL_CONTEXT):
        drops = ceil_div(width, roll_width)
        cut_length_in = ceil_to_multiple(
            height + policy.trim_allowance_in, repeat
        )
        total_in = drops * cut_length_in
        raw_ly = total_in / _IN_PER_LY
        waste = policy.waste_for(defn.wc_tag)
        with_waste_ly = raw_ly * (Decimal(1) + waste)
        net_area_sf = (width * height) / Decimal(144)
    return QuantityResult(
        application_id=None,
        method=TakeoffMethod.STRIP,
        drops=int(drops),
        cut_length_in=cut_length_in,
        net_area_sf=net_area_sf,
        raw_qty=raw_ly,
        with_waste_qty=with_waste_ly,
        unit=defn.unit_of_sale,
    )


def compute_quantity_area(
    net_area_sf: Decimal,
    defn: WCDefinition,
    policy: WastePolicy,
) -> QuantityResult:
    """compute_quantity_area(net_area_sf, defn, policy) -> QuantityResult

    Frozen interface ComputeQuantityArea (FR-5, ADR-006):
    net_sy = net_area_sf/9; order_sy = net_sy*(1+waste);
    units = ceil(order_sy/coverage_per_unit_sy) — the final ceil to whole
    sale units is taken at the aggregation line level (FR-6), keeping raw
    and with-waste figures exact and distinct here.
    """
    _require_decimal(defn, "yield_per_unit")
    area = exact(net_area_sf)
    with localcontext(DECIMAL_CONTEXT):
        net_sy = area / _SF_PER_SY
        waste = policy.waste_for(defn.wc_tag)
        order_sy = net_sy * (Decimal(1) + waste)
    return QuantityResult(
        application_id=None,
        method=TakeoffMethod.AREA,
        drops=None,
        cut_length_in=None,
        net_area_sf=area,
        raw_qty=net_sy,
        with_waste_qty=order_sy,
        unit=defn.unit_of_sale,
    )
