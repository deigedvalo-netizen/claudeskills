"""VisionPrefillAdapter: deferred v1.1 opt-in vision pre-fill.

Requirement ids: FR-3, FR-4, NFR-3, NFR-4 (ADR-004, ADR-011).

Pre-fills the same editable forms with proposed values plus source and
confidence, routing low-confidence proposals to the review queue. It is
opt-in, clearly labelled as leaving the machine, and structurally
incapable of invoking the compute path: this module imports nothing
from wctakeoff.math, wctakeoff.geometry or wctakeoff.aggregate, and the
anthropic client (pinned 0.34.2 in technology_choices) is imported
lazily ONLY inside the opt-in call, so the v1 offline build has no
network client on any import path (NFR-3).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from wctakeoff.domain.models import Flag, Proposal, Sheet, SubjectRef
from wctakeoff.domain.units import FlagKind
from wctakeoff.review.flags import FlagRegistry

#: Proposals below this confidence are routed to review (ADR-004).
LOW_CONFIDENCE_THRESHOLD = Decimal("0.80")


class VisionNotEnabledError(RuntimeError):
    """Raised when propose() is called without explicit opt-in (NFR-3)."""


class VisionPrefillAdapter:
    """Opt-in v1.1 adapter; every proposal is provisional (NFR-4)."""

    _LABEL = "vision-prefill (leaves this machine)"

    def __init__(
        self,
        flags: FlagRegistry,
        *,
        opted_in: bool = False,
    ) -> None:
        self._flags = flags
        self._opted_in = opted_in
        self._client: Any = None

    def opt_in(self) -> None:
        """Explicit estimator opt-in; without it no network call happens."""
        self._opted_in = True

    def _ensure_client(self) -> Any:
        """Lazy-import the anthropic SDK (0.34.2) only after opt-in.

        Keeping the import inside this method means the v1 build path
        never imports a network client (NFR-3, ADR-004).
        """
        if self._client is None:
            import anthropic  # noqa: PLC0415  (lazy by design, NFR-3)

            self._client = anthropic.Anthropic()
        return self._client

    def propose(self, sheet: Sheet) -> list[Proposal]:
        """ExtractionAdapter.propose: provisional pre-fill for one sheet.

        Refuses to run without opt-in. Proposals are never confirmed
        here (confirmed=False always); low-confidence ones additionally
        raise an UNREADABLE_DIMENSION flag routing them to review.
        """
        if not self._opted_in:
            raise VisionNotEnabledError(
                "vision pre-fill is opt-in and leaves this machine; call "
                "opt_in() first (NFR-3, NFR-4)"
            )
        self._ensure_client()
        # v1.1 surface: the extraction prompt/response mapping is the
        # adapter's own concern and produces Proposal objects. The v1
        # tree ships the boundary and the review routing; no proposals
        # are fabricated here.
        proposals: list[Proposal] = []
        return self._route_low_confidence(sheet, proposals)

    def _route_low_confidence(
        self, sheet: Sheet, proposals: list[Proposal]
    ) -> list[Proposal]:
        for proposal in proposals:
            if proposal.confidence < LOW_CONFIDENCE_THRESHOLD:
                self._flags.raise_flag(
                    Flag(
                        kind=FlagKind.UNREADABLE_DIMENSION,
                        subject_ref=SubjectRef(
                            kind="field",
                            ref_id=(
                                f"{proposal.field_ref.subject.ref_id}."
                                f"{proposal.field_ref.field_name}"
                            ),
                        ),
                        source_sheet_id=sheet.sheet_id,
                        blocks=[
                            f"confirm:{proposal.field_ref.field_name}"
                        ],
                        detail=(
                            "vision proposal below confidence threshold "
                            f"({proposal.confidence} < "
                            f"{LOW_CONFIDENCE_THRESHOLD}); routed to review"
                        ),
                    )
                )
        return proposals

    def source_label(self) -> str:
        """ExtractionAdapter.source_label; clearly marked as remote."""
        return self._LABEL
