"""Printable per-WC summary export (ReportLab 4.2.2), fully offline.

Requirement ids: FR-7 (ADR-006, ADR-007, ADR-010).

Includes the order lines with raw and with-waste side by side, the
set-read reference block labelled as non-computed, and the policy
summary the numbers were produced under.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from wctakeoff.domain.units import UNKNOWN
from wctakeoff.presentation.presenter import TakeoffView, format_qty

_GRID = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
)


def _verbatim(value: object) -> str:
    if value is UNKNOWN:
        return "UNKNOWN"
    return getattr(value, "value", str(value))


def write_pdf(view: TakeoffView, dest: Path) -> Path:
    """Write the printable takeoff summary document."""
    styles = getSampleStyleSheet()
    story: list[object] = [
        Paragraph("Wallcovering Takeoff — Order Summary", styles["Title"]),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "Each WC is listed in its own unit of sale; no combined total "
            "is shown (per-WC unit fidelity).",
            styles["Italic"],
        ),
        Spacer(1, 0.15 * inch),
    ]

    line_rows: list[list[str]] = [
        ["WC Tag", "Raw Qty", "With-Waste Qty", "Order Qty", "Unit"]
    ]
    for line_view in view.lines:
        line = line_view.line
        line_rows.append(
            [
                line.wc_tag,
                format_qty(line.raw_qty),
                format_qty(line.with_waste_qty),
                format_qty(line.order_qty),
                line.unit.value,
            ]
        )
    story.append(Table(line_rows, style=_GRID, hAlign="LEFT"))
    story.append(Spacer(1, 0.25 * inch))

    story.append(
        Paragraph(
            "Set-Read Reference (verbatim from schedule — NOT computed)",
            styles["Heading2"],
        )
    )
    setread_rows: list[list[str]] = [
        ["WC", "Manufacturer", "Pattern", "Roll W (in)", "Repeat (in)", "Match", "Unit", "Yield"]
    ]
    for defn in view.set_read_block:
        setread_rows.append(
            [
                defn.wc_tag,
                _verbatim(defn.manufacturer),
                _verbatim(defn.pattern_name),
                _verbatim(defn.roll_width_in),
                _verbatim(defn.repeat_in),
                _verbatim(defn.match_type),
                defn.unit_of_sale.value,
                _verbatim(defn.yield_per_unit),
            ]
        )
    story.append(Table(setread_rows, style=_GRID, hAlign="LEFT"))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Policy Summary", styles["Heading2"]))
    policy = view.policy_summary
    policy_rows = [
        ["Setting", "Value"],
        ["Waste %", format_qty(policy.waste_pct)],
        ["Deduct openings", str(policy.deduct_openings)],
        ["Opening threshold (sf)", format_qty(policy.opening_threshold_sf)],
        ["Trim allowance (in)", format_qty(policy.trim_allowance_in)],
    ]
    for wc_tag, waste in sorted(policy.per_wc_waste.items()):
        policy_rows.append([f"Waste % override [{wc_tag}]", format_qty(waste)])
    story.append(Table(policy_rows, style=_GRID, hAlign="LEFT"))

    document = SimpleDocTemplate(str(dest), pagesize=letter)
    document.build(story)
    return dest
