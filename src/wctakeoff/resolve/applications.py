"""ApplicationResolver: WC tags onto concrete (room, wall) applications.

Requirement ids: FR-3, FR-8 (ADR-008, ARCH-A4).

A room-level blanket note is a default across that room's explicit wall
set; a wall-level tag overrides the default for that wall only. Any
room whose resolution is ambiguous raises UNRESOLVED_UNO and is not
guessed; a tag with no matching WC definition raises UNDEFINED_WC.
"""
from __future__ import annotations

from typing import Callable, Sequence

from wctakeoff.domain.ids import RoomId, SetId, new_application_id
from wctakeoff.domain.models import (
    Application,
    ApplicationResolution,
    Flag,
    Room,
    RoomNote,
    SubjectRef,
    WallTag,
)
from wctakeoff.domain.units import FlagKind
from wctakeoff.domain.wc_definition import SetReadRegistry
from wctakeoff.resolve.overrides import extract_wc_tag, is_v1_tag, origin_for

#: Injected room lookup; the resolver never owns room storage.
RoomsProvider = Callable[[SetId], Sequence[Room]]


class ApplicationResolver:
    """Resolves tags to applications, flagging every ambiguity (FR-3)."""

    def __init__(
        self,
        registry: SetReadRegistry,
        rooms_provider: RoomsProvider,
    ) -> None:
        self._registry = registry
        self._rooms_provider = rooms_provider

    def resolve_applications(
        self,
        set_id: SetId,
        room_notes: Sequence[RoomNote],
        wall_tags: Sequence[WallTag],
    ) -> ApplicationResolution:
        """resolve_applications(set_id, room_notes, wall_tags)

        Frozen interface ResolveApplications (FR-3, FR-8, ADR-008).
        Wall-level tag overrides room-level default. Returns the
        applications plus the ambiguity flags; the caller registers the
        flags with the FlagRegistry (raise_flag) so they gate computation.
        """
        rooms: dict[RoomId, Room] = {
            room.room_id: room for room in self._rooms_provider(set_id)
        }
        applications: list[Application] = []
        ambiguous: list[Flag] = []
        seen: set[tuple[str, RoomId, str]] = set()

        overridden: set[tuple[RoomId, str]] = {
            (tag.room_id, str(tag.wall_id)) for tag in wall_tags
        }

        def add(
            wc_tag: str,
            room_id: RoomId,
            wall_id: str,
            origin_flag: Application,
        ) -> None:
            key = (wc_tag, room_id, wall_id)
            if key in seen:
                return
            seen.add(key)
            applications.append(origin_flag)

        # Wall-level tags first: they win over any room default (ADR-008).
        for tag in wall_tags:
            if not is_v1_tag(tag.wc_tag):
                continue  # out-of-scope finish families are ignored (ARCH-A9)
            if self._registry.get_wc_definition(tag.wc_tag) is None:
                ambiguous.append(
                    Flag(
                        kind=FlagKind.UNDEFINED_WC,
                        subject_ref=SubjectRef(kind="wc_tag", ref_id=tag.wc_tag),
                        source_sheet_id=tag.source_sheet_id,
                        blocks=[f"quantity:{tag.wc_tag}"],
                        detail=(
                            f"tag {tag.wc_tag} applied to wall {tag.wall_id} "
                            "has no schedule definition (UNDEFINED_WC)"
                        ),
                    )
                )
                continue
            add(
                tag.wc_tag,
                tag.room_id,
                str(tag.wall_id),
                Application(
                    application_id=new_application_id(),
                    wc_tag=tag.wc_tag,
                    room_id=tag.room_id,
                    wall_id=tag.wall_id,
                    origin=origin_for(tag.from_elevation, is_override=True),
                    source_sheet_id=tag.source_sheet_id,
                ),
            )

        # Room-level blanket notes fill every non-overridden wall (ADR-008).
        for note in room_notes:
            room = rooms.get(note.room_id)
            subject = SubjectRef(kind="room", ref_id=str(note.room_id))
            if room is None or not room.walls:
                ambiguous.append(
                    Flag(
                        kind=FlagKind.UNRESOLVED_UNO,
                        subject_ref=subject,
                        source_sheet_id=note.source_sheet_id,
                        blocks=[f"applications:{note.room_id}"],
                        detail=(
                            f"blanket note {note.text!r} targets room "
                            f"{note.room_id} with no established wall set; "
                            "resolution is ambiguous (ADR-008)"
                        ),
                    )
                )
                continue
            wc_tag = extract_wc_tag(note.text)
            if wc_tag is None or not is_v1_tag(wc_tag):
                ambiguous.append(
                    Flag(
                        kind=FlagKind.UNRESOLVED_UNO,
                        subject_ref=subject,
                        source_sheet_id=note.source_sheet_id,
                        blocks=[f"applications:{note.room_id}"],
                        detail=(
                            f"blanket note {note.text!r} does not name exactly "
                            "one in-scope WC tag; routed to review, not guessed"
                        ),
                    )
                )
                continue
            if self._registry.get_wc_definition(wc_tag) is None:
                ambiguous.append(
                    Flag(
                        kind=FlagKind.UNDEFINED_WC,
                        subject_ref=SubjectRef(kind="wc_tag", ref_id=wc_tag),
                        source_sheet_id=note.source_sheet_id,
                        blocks=[f"quantity:{wc_tag}"],
                        detail=(
                            f"blanket note names {wc_tag} but the schedule "
                            "defines no such WC (UNDEFINED_WC)"
                        ),
                    )
                )
                continue
            for wall in room.walls:
                if (room.room_id, str(wall.wall_id)) in overridden:
                    continue  # wall-level tag replaced the default (ADR-008)
                add(
                    wc_tag,
                    room.room_id,
                    str(wall.wall_id),
                    Application(
                        application_id=new_application_id(),
                        wc_tag=wc_tag,
                        room_id=room.room_id,
                        wall_id=wall.wall_id,
                        origin=origin_for(False, is_override=False),
                        source_sheet_id=note.source_sheet_id,
                    ),
                )

        # A defined WC never applied anywhere is worth surfacing (FR-8).
        used_tags = {a.wc_tag for a in applications}
        for defn in self._registry.all_definitions():
            if defn.wc_tag not in used_tags:
                ambiguous.append(
                    Flag(
                        kind=FlagKind.UNUSED_WC,
                        subject_ref=SubjectRef(kind="wc_tag", ref_id=defn.wc_tag),
                        source_sheet_id=defn.source_sheet_id,
                        blocks=[],
                        detail=(
                            f"{defn.wc_tag} is defined in the schedule but "
                            "resolved onto no wall (UNUSED_WC; non-blocking)"
                        ),
                    )
                )

        return ApplicationResolution(
            applications=applications, ambiguous=ambiguous
        )
