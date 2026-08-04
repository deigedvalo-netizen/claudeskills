"""Drawing-scale detection from a sheet's own printed scale note.

Requirement ids: FR-1, FR-4, NFR-1 (ARCH-A2, ADR-005).

A drawing states its own scale in the title block: ``SCALE: 1/4" = 1'-0"``.
That note plus the page's true geometry determines the pixel-to-inches
conversion exactly, with no estimation: a PDF page is measured in points
(72 to the paper inch), so once a page is rasterised at a known
resolution the number of pixels per paper inch is known, and the note
supplies how many real inches one paper inch represents.

This stays inside ARCH-A2. The scale is read from printed text on the
sheet, exactly as an estimator would read it; it is never inferred from
the geometry of the linework. Where the note is absent, unreadable, or
contradicted by another note on the same page, detection reports nothing
and the estimator calibrates by hand — a wrong scale silently corrupts
every measurement downstream, so guessing is the one thing this module
must never do (ADR-005).

Pure: no PDF library, no Qt, no I/O. Callers pass text and geometry.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Final, NamedTuple, Sequence

_POINTS_PER_INCH: Final[Decimal] = Decimal(72)
_INCHES_PER_FOOT: Final[Decimal] = Decimal(12)

#: An explicit refusal printed on the sheet. Recognised so it can be
#: reported as "the drawing says not to scale" rather than "no note found".
_NOT_TO_SCALE = re.compile(r"\bN\.?\s?T\.?\s?S\.?\b|\bNOT\s+TO\s+SCALE\b", re.I)

#: ``1/4" = 1'-0"``, ``1/4"=1'``, ``3/32" = 1'-0"``, ``1" = 20'-0"``.
#: The paper side is inches; the real side is feet with optional inches.
_ARCHITECTURAL = re.compile(
    r"""
    (?<![\d./])                                   # never start mid-number
    (?:(?P<paper_whole>\d+)[ \t]+)?               # 1 (of "1 1/2"), same line
    (?P<paper>\d+(?:\.\d+)?(?:\s*/\s*\d+)?)       # 1/4  or  1  or  1.5
    \s*(?:"|''|\bin\b)?
    \s*=\s*
    (?P<feet>\d+(?:\.\d+)?)\s*(?:'|\bft\b)        # 1'   or  20'
    (?:\s*-?\s*(?P<inches>\d+(?:\.\d+)?)\s*(?:"|''))?   # optional -0"
    """,
    re.VERBOSE | re.IGNORECASE,
)

#: Metric/engineering ratio: ``1:50`` means one paper unit is 50 real units.
_RATIO = re.compile(r"\b1\s*:\s*(?P<denominator>\d{1,5})\b")


class DetectedScale(NamedTuple):
    """A scale read off the sheet, with everything needed to audit it."""

    inches_per_pixel: Decimal
    #: Real inches represented by one inch of paper (48 for 1/4" = 1'-0").
    real_inches_per_paper_inch: Decimal
    #: Rendered pixels per inch of paper, from the page's true geometry.
    pixels_per_paper_inch: Decimal
    #: The note as printed, quoted back so the estimator can check it.
    note: str

    def describe(self) -> str:
        """Provenance line naming the note the scale came from (NFR-1)."""
        return (
            f"drawing scale note “{self.note}” "
            f"({self.inches_per_pixel.quantize(Decimal('0.000001'))} in/px)"
        )


def _tidy(value: Decimal) -> Decimal:
    """Drop trailing zeros without falling into exponent notation.

    Plain `normalize()` renders 200 as ``2.0E+2``, which is correct but
    unreadable in a provenance line an estimator has to audit.
    """
    normalised = value.normalize()
    _sign, _digits, exponent = normalised.as_tuple()
    if isinstance(exponent, int) and exponent > 0:
        return normalised.quantize(Decimal(1))
    return normalised


def _fraction(text: str) -> Decimal | None:
    """Read ``1/4``, ``3/32``, ``1.5`` or ``2`` as an exact Decimal."""
    cleaned = text.strip().replace(" ", "")
    if not cleaned:
        return None
    if "/" in cleaned:
        numerator, _, denominator = cleaned.partition("/")
        try:
            bottom = Decimal(denominator)
            if bottom == 0:
                return None
            return Decimal(numerator) / bottom
        except Exception:
            return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def scale_ratios(text: str) -> list[tuple[Decimal, str]]:
    """Every distinct scale stated in the given page text.

    Returns (real inches per paper inch, note as printed) pairs. More than
    one distinct value means the page carries details drawn at different
    scales, which no single page-wide conversion can serve.
    """
    found: list[tuple[Decimal, str]] = []
    seen: set[Decimal] = set()

    for match in _ARCHITECTURAL.finditer(text):
        paper = _fraction(match.group("paper"))
        if paper is None or paper <= 0:
            continue
        whole = match.group("paper_whole")
        if whole:
            leading = _fraction(whole)
            if leading is None:
                continue
            paper += leading
        real = Decimal(match.group("feet")) * _INCHES_PER_FOOT
        if match.group("inches"):
            real += Decimal(match.group("inches"))
        if real <= 0:
            continue
        ratio = real / paper
        if ratio not in seen:
            seen.add(ratio)
            found.append((ratio, match.group(0).strip()))

    if not found:
        for match in _RATIO.finditer(text):
            denominator = Decimal(match.group("denominator"))
            if denominator <= 1:
                continue
            if denominator not in seen:
                seen.add(denominator)
                found.append((denominator, match.group(0).strip()))

    return found


def says_not_to_scale(text: str) -> bool:
    """Whether the sheet explicitly declares itself not to scale."""
    return bool(_NOT_TO_SCALE.search(text or ""))


def pixels_per_paper_inch(
    page_width_points: Decimal, rendered_width_pixels: Decimal
) -> Decimal | None:
    """Rendered resolution derived from the page's own geometry.

    Computed from the actual rasterised width rather than assuming the
    nominal DPI, so any rounding in the renderer is absorbed here instead
    of biasing every measurement on the sheet.
    """
    if page_width_points <= 0 or rendered_width_pixels <= 0:
        return None
    paper_inches = page_width_points / _POINTS_PER_INCH
    if paper_inches <= 0:
        return None
    return _tidy(rendered_width_pixels / paper_inches)


def detect_page_scale(
    page_text: str,
    page_width_points: Decimal,
    rendered_width_pixels: Decimal,
) -> DetectedScale | None:
    """Derive a page's scale from its printed note and true geometry.

    Returns None — never a fallback value — when the page states no
    scale, states more than one, declares itself not to scale, or has
    geometry that cannot be read. In every one of those cases the
    estimator calibrates by hand instead (ADR-005).
    """
    text = page_text or ""
    if says_not_to_scale(text):
        return None

    ratios = scale_ratios(text)
    if len(ratios) != 1:
        return None  # none stated, or several — no page-wide conversion

    resolution = pixels_per_paper_inch(
        page_width_points, rendered_width_pixels
    )
    if resolution is None:
        return None

    real_per_paper, note = ratios[0]
    return DetectedScale(
        inches_per_pixel=real_per_paper / resolution,
        real_inches_per_paper_inch=real_per_paper,
        pixels_per_paper_inch=resolution,
        note=note,
    )


def describe_candidates(text: str) -> Sequence[str]:
    """The scale notes found on a page, for reporting an ambiguous sheet."""
    return [note for _ratio, note in scale_ratios(text or "")]
