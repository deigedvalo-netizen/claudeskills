"""Pure measurement core for on-drawing scale calibration and takeoff.

Requirement ids: FR-4, NFR-1 (ARCH-A2, ADR-003, ADR-011).

Scale calibration and pixel measurement, with no Qt import and no I/O, so
every formula here is verifiable headlessly. ARCH-A2 permits pixel
measurement only as a labelled cross-check that is never silently treated
as a printed dimension: every value produced here is tagged with its
provenance and the calibration it came from, and still has to pass the
confirmation gate before it can reach the math core (ADR-011).

All arithmetic is Decimal (ADR-003). Screen coordinates arrive from Qt as
floats and are converted at the boundary by `from_float`, which is the one
sanctioned float entry point in this module.
"""
from __future__ import annotations

import re
from decimal import Context, Decimal
from typing import Final, NamedTuple, Sequence

#: Working precision for calibration and measurement (ADR-003 uses 28).
MEASURE_CONTEXT: Final[Context] = Context(prec=28)

#: Measured lengths are reported to the nearest 1/16 inch, the finest
#: increment a construction drawing is dimensioned to in practice.
_INCH_DENOMINATOR: Final[Decimal] = Decimal(16)

_INCHES_PER_FOOT: Final[Decimal] = Decimal(12)
_SQIN_PER_SQFT: Final[Decimal] = Decimal(144)


class LengthParseError(ValueError):
    """The typed length could not be read as a construction dimension."""


class ScaleUncalibratedError(RuntimeError):
    """A measurement was requested on a sheet with no calibration.

    Raised rather than assuming a default scale: a guessed scale would be
    a fabricated dimension, which ADR-005 forbids outright.
    """


class Point(NamedTuple):
    """A point in sheet-image pixel space."""

    x: Decimal
    y: Decimal


class Calibration(NamedTuple):
    """The pixel-to-inches scale established for one sheet.

    `inches_per_pixel` is derived from a single estimator-drawn reference
    span whose real length they typed from the drawing's own printed
    dimension, so the calibration is traceable back to printed text
    (ARCH-A2) rather than invented from page geometry.
    """

    inches_per_pixel: Decimal
    reference_pixels: Decimal
    reference_inches: Decimal

    def describe(self) -> str:
        """Human-readable provenance line for the trace ledger (NFR-1)."""
        return (
            f"{format_inches(self.reference_inches)} measured across "
            f"{self.reference_pixels.quantize(Decimal('0.1'))} px "
            f"({self.inches_per_pixel.quantize(Decimal('0.000001'))} in/px)"
        )


def from_float(value: float) -> Decimal:
    """Convert one Qt screen coordinate into an exact Decimal.

    Qt hands back float coordinates; `str` round-trips the shortest exact
    representation, which keeps the rest of the module float-free.
    """
    return Decimal(str(value))


_FEET_INCHES = re.compile(
    r"""
    ^\s*
    (?:(?P<feet>\d+(?:\.\d+)?)\s*(?:'|ft\b|feet\b|foot\b))?   # 20'  20 ft
    \s*[-\s]?\s*
    (?:
        (?P<inches>\d+(?:\.\d+)?)?                             # 6
        \s*
        (?:(?P<num>\d+)\s*/\s*(?P<den>\d+))?                   # 1/2
        \s*
        (?:"|''|in\b|inch\b|inches\b)?
    )?
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)


def parse_length_inches(text: str) -> Decimal:
    """Read a construction dimension as an exact number of inches.

    Accepts the notations an estimator actually types off a drawing:
    ``246``, ``246"``, ``20'``, ``20'6"``, ``20'-6"``, ``20' 6 1/2"``,
    ``20.5'``, ``6 1/2``, ``20 ft 6 in``. A bare number is inches.

    Raises LengthParseError rather than defaulting, so an unreadable entry
    can never become a silent zero (ADR-005).
    """
    raw = text.strip()
    if not raw:
        raise LengthParseError("empty length")
    if raw[0] in "+-":
        # A leading sign would otherwise be swallowed by the feet-inches
        # separator, turning "-5" into a positive 5 inches.
        raise LengthParseError(f"{text!r} is not a positive length")

    match = _FEET_INCHES.match(raw)
    if match is None:
        raise LengthParseError(f"{text!r} is not a readable dimension")

    feet_text = match.group("feet")
    inches_text = match.group("inches")
    numerator_text = match.group("num")
    denominator_text = match.group("den")

    if feet_text is None and inches_text is None and numerator_text is None:
        raise LengthParseError(f"{text!r} contains no number")

    total = Decimal(0)
    if feet_text is not None:
        total += Decimal(feet_text) * _INCHES_PER_FOOT
    if inches_text is not None:
        total += Decimal(inches_text)
    if numerator_text is not None and denominator_text is not None:
        denominator = Decimal(denominator_text)
        if denominator == 0:
            raise LengthParseError(f"{text!r} has a zero denominator")
        total += Decimal(numerator_text) / denominator
    elif numerator_text is not None or denominator_text is not None:
        raise LengthParseError(f"{text!r} has an incomplete fraction")

    if total <= 0:
        raise LengthParseError(f"{text!r} is not a positive length")
    return total


def format_inches(value: Decimal) -> str:
    """Render inches as feet-inches with a sixteenth fraction.

    240 -> ``20'-0"``; 246.5 -> ``20'-6 1/2"``; 6.25 -> ``0'-6 1/4"``.
    """
    sixteenths = (value * _INCH_DENOMINATOR).quantize(Decimal(1))
    whole_inches, remainder = divmod(sixteenths, _INCH_DENOMINATOR)
    feet, inches = divmod(whole_inches, _INCHES_PER_FOOT)

    if remainder == 0:
        return f"{feet}'-{inches}\""

    numerator = int(remainder)
    denominator = int(_INCH_DENOMINATOR)
    while numerator % 2 == 0 and denominator % 2 == 0:
        numerator //= 2
        denominator //= 2
    return f"{feet}'-{inches} {numerator}/{denominator}\""


def distance_pixels(start: Point, end: Point) -> Decimal:
    """Euclidean pixel distance between two clicked points."""
    dx = end.x - start.x
    dy = end.y - start.y
    return MEASURE_CONTEXT.sqrt(dx * dx + dy * dy)


def calibrate(
    start: Point, end: Point, known_length: Decimal
) -> Calibration:
    """Establish a sheet's scale from one span of known printed length.

    The estimator draws across a dimension whose printed value they type
    in; the ratio becomes the sheet's scale. A zero-length span is refused
    rather than producing an infinite scale.
    """
    pixels = distance_pixels(start, end)
    if pixels <= 0:
        raise ScaleUncalibratedError(
            "the calibration span has zero length; draw across a printed "
            "dimension and try again"
        )
    if known_length <= 0:
        raise LengthParseError("the known length must be positive")
    return Calibration(
        inches_per_pixel=MEASURE_CONTEXT.divide(known_length, pixels),
        reference_pixels=pixels,
        reference_inches=known_length,
    )


def measure_length_inches(
    start: Point, end: Point, calibration: Calibration | None
) -> Decimal:
    """Real-world length of a two-point span, in inches."""
    if calibration is None:
        raise ScaleUncalibratedError(
            "this sheet has no scale yet; calibrate against a printed "
            "dimension before measuring"
        )
    return distance_pixels(start, end) * calibration.inches_per_pixel


def polygon_area_pixels(points: Sequence[Point]) -> Decimal:
    """Shoelace area of a closed polygon, in square pixels.

    The polygon is treated as implicitly closed; orientation is ignored,
    so a clockwise and a counter-clockwise trace of the same outline give
    the same area.
    """
    if len(points) < 3:
        raise ValueError("an area needs at least three points")
    total = Decimal(0)
    for index, current in enumerate(points):
        following = points[(index + 1) % len(points)]
        total += current.x * following.y - following.x * current.y
    return abs(total) / Decimal(2)


def measure_area_sf(
    points: Sequence[Point], calibration: Calibration | None
) -> Decimal:
    """Real-world area of a traced polygon, in square feet."""
    if calibration is None:
        raise ScaleUncalibratedError(
            "this sheet has no scale yet; calibrate against a printed "
            "dimension before measuring"
        )
    square_inches = polygon_area_pixels(points) * (
        calibration.inches_per_pixel * calibration.inches_per_pixel
    )
    return square_inches / _SQIN_PER_SQFT


def format_area_sf(value: Decimal) -> str:
    """Render a measured area for display, to two decimals."""
    return f"{value.quantize(Decimal('0.01'))} sf"
