"""FlagRegistry: the blocking review queue.

Requirement ids: FR-8, FR-2, FR-3, FR-4 (ADR-005).

Any missing, ambiguous or contradictory input is recorded as a typed
Flag carrying its originating sheet, its subject and what it blocks.
A non-empty blocking_flags_for result MUST prevent computation of any
dependent quantity — flag rather than guess, always.
"""
from __future__ import annotations

from wctakeoff.domain.ids import FlagId, new_flag_id
from wctakeoff.domain.models import Flag, SubjectRef


class FlagRegistry:
    """Owns the review queue and answers blocking queries (FR-8)."""

    def __init__(self) -> None:
        self._flags: dict[FlagId, Flag] = {}
        self._resolved: set[FlagId] = set()

    def raise_flag(self, flag: Flag) -> FlagId:
        """raise_flag(flag: Flag) -> FlagId

        Frozen interface RaiseFlag (FR-8). Assigns the flag_id if the
        caller did not, stores the flag, and returns its id.
        """
        flag_id = flag.flag_id if flag.flag_id is not None else new_flag_id()
        stored = flag.model_copy(update={"flag_id": flag_id}) if flag.flag_id is None else flag
        self._flags[flag_id] = stored
        return flag_id

    def blocking_flags_for(self, subject_ref: SubjectRef) -> list[Flag]:
        """blocking_flags_for(subject_ref: SubjectRef) -> list[Flag]

        Frozen interface BlockingFlagsFor (FR-8, ADR-005). A non-empty
        result MUST prevent computation of any dependent quantity; the
        compute path consults this before producing a number.
        """
        return [
            f
            for fid, f in self._flags.items()
            if fid not in self._resolved
            and f.subject_ref == subject_ref
            and f.blocks
        ]

    def resolve(self, flag_id: FlagId) -> None:
        """Mark a flag resolved after the estimator addresses it."""
        if flag_id in self._flags:
            self._resolved.add(flag_id)

    def open_flags(self) -> list[Flag]:
        """All unresolved flags, for the review-queue panel (FR-7, FR-8)."""
        return [f for fid, f in self._flags.items() if fid not in self._resolved]

    def get(self, flag_id: FlagId) -> Flag | None:
        """Look up one flag by id (open or resolved)."""
        return self._flags.get(flag_id)

    def open_blocking_flags(self) -> list[Flag]:
        """All unresolved flags that block something (finalisation gate)."""
        return [f for f in self.open_flags() if f.blocks]
