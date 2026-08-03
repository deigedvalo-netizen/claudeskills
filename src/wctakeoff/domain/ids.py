"""Typed identifiers for the wallcovering-takeoff domain.

Requirement ids: FR-2, NFR-1, NFR-2.

Every entity carries a stable, typed identity so that provenance (NFR-1)
and reload-identical recomputation (NFR-2) can key off values that never
collide across entity kinds. Identities are uuid4 strings wrapped in
NewType so a SheetId cannot be passed where a WallId is expected.
"""
from __future__ import annotations

import uuid
from typing import NewType

SetId = NewType("SetId", str)
SheetId = NewType("SheetId", str)
RoomId = NewType("RoomId", str)
WallId = NewType("WallId", str)
OpeningId = NewType("OpeningId", str)
ApplicationId = NewType("ApplicationId", str)
FlagId = NewType("FlagId", str)
ValueId = NewType("ValueId", str)


def new_set_id() -> SetId:
    """Mint a DrawingSet primary key (uuid4 per the data model)."""
    return SetId(str(uuid.uuid4()))


def new_sheet_id() -> SheetId:
    return SheetId(str(uuid.uuid4()))


def new_room_id() -> RoomId:
    return RoomId(str(uuid.uuid4()))


def new_wall_id() -> WallId:
    return WallId(str(uuid.uuid4()))


def new_opening_id() -> OpeningId:
    return OpeningId(str(uuid.uuid4()))


def new_application_id() -> ApplicationId:
    return ApplicationId(str(uuid.uuid4()))


def new_flag_id() -> FlagId:
    return FlagId(str(uuid.uuid4()))


def new_value_id() -> ValueId:
    return ValueId(str(uuid.uuid4()))
