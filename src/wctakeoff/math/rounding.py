"""Deterministic Decimal context and rounding primitives for the math core.

Requirement ids: FR-5, FR-6, NFR-2 (ADR-003).

All arithmetic in the math core runs under one explicitly set Decimal
context so identical inputs give bit-identical results across runs and
platforms. Rounding to a sale unit is always UP; intermediate areas are
never rounded down. No I/O, no clock, no randomness, no global mutable
state beyond the fixed context constants.
"""
from __future__ import annotations

from decimal import ROUND_CEILING, Context, Decimal, localcontext
from typing import Final

#: Explicit context (ADR-003): enough precision that ceil boundaries are
#: exact for any realistic dimension; deterministic across platforms.
DECIMAL_CONTEXT: Final[Context] = Context(prec=28)

_ONE: Final[Decimal] = Decimal(1)


def ceil_decimal(value: Decimal) -> Decimal:
    """Ceiling to a whole number, exactly, under the fixed context."""
    with localcontext(DECIMAL_CONTEXT):
        return value.to_integral_value(rounding=ROUND_CEILING)


def ceil_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    """ceil(numerator / denominator) as an exact whole Decimal.

    The ceil-at-boundary behaviour is the reason for Decimal (ADR-003):
    a boundary value must land on the same side of the integer step on
    every run and machine.
    """
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    with localcontext(DECIMAL_CONTEXT):
        return ceil_decimal(numerator / denominator)


def ceil_to_multiple(value: Decimal, multiple: Decimal) -> Decimal:
    """Round value UP to the next multiple (repeat rounding, FR-5)."""
    if multiple <= 0:
        raise ValueError("multiple must be > 0")
    with localcontext(DECIMAL_CONTEXT):
        return ceil_div(value, multiple) * multiple


def round_up_to_sale_unit(value: Decimal) -> Decimal:
    """Round an order quantity UP to a whole sale unit; never down (FR-6)."""
    return ceil_to_multiple(value, _ONE)


def exact(value: Decimal | int | str) -> Decimal:
    """Construct a Decimal without ever passing through binary float.

    Floats are rejected outright so no call site can accidentally coerce
    (ADR-003 standing review check).
    """
    if isinstance(value, float):
        raise TypeError(
            "float is forbidden in the math core; pass Decimal, int or str "
            "(ADR-003)"
        )
    return Decimal(value)
