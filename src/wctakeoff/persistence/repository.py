"""ProjectRepository: the single persistence boundary.

Requirement ids: NFR-2 (ADR-001, ARCH-A10).

Persists the whole project to one local SQLite file via the stdlib
sqlite3 driver (pinned SQLite 3.45.3 in technology_choices) so that
reopening a project and recomputing yields byte-identical results.
Decimals are stored as TEXT verbatim — never through float — and the
UNKNOWN sentinel round-trips as the literal string 'UNKNOWN' (ADR-002).
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from decimal import Decimal
from importlib import resources
from pathlib import Path

from wctakeoff.domain.ids import (
    FlagId,
    OpeningId,
    RoomId,
    SetId,
    SheetId,
    WallId,
    new_set_id,
)
from wctakeoff.domain.models import (
    DrawingSet,
    Flag,
    Opening,
    PolicySnapshot,
    Room,
    Sheet,
    SubjectRef,
    Wall,
)
from wctakeoff.domain.units import (
    UNKNOWN,
    ApplicationOrigin,
    FlagKind,
    MatchType,
    SheetRole,
    UnitOfSale,
    Unknown as _Unknown,
)
from wctakeoff.domain.models import Application
from wctakeoff.domain.wc_definition import WCDefinition

_UNKNOWN_LITERAL = "UNKNOWN"


def _enc(value: object) -> str:
    """Encode a SET READ scalar verbatim; UNKNOWN as its literal."""
    if value is UNKNOWN:
        return _UNKNOWN_LITERAL
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, MatchType):
        return value.value
    return str(value)

def _dec_decimal(text: str) -> "Decimal | _Unknown":
    return UNKNOWN if text == _UNKNOWN_LITERAL else Decimal(text)


def _dec_str(text: str) -> "str | _Unknown":
    return UNKNOWN if text == _UNKNOWN_LITERAL else text


def _dec_match(text: str) -> "MatchType | _Unknown":
    return UNKNOWN if text == _UNKNOWN_LITERAL else MatchType(text)


def _opt_decimal(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


class ProjectRepository:
    """Whole-project save/load against a single SQLite file (NFR-2)."""

    def __init__(self) -> None:
        self._drawing_sets: dict[SetId, DrawingSet] = {}
        self._rooms: dict[SetId, list[Room]] = {}
        self._definitions: dict[SetId, list[WCDefinition]] = {}
        self._applications: dict[SetId, list[Application]] = {}
        self._policies: dict[SetId, PolicySnapshot] = {}
        self._flags: dict[SetId, list[Flag]] = {}

    # -- in-memory project state fed by the services ---------------------

    def put_drawing_set(self, drawing_set: DrawingSet) -> None:
        self._drawing_sets[drawing_set.set_id] = drawing_set

    def put_rooms(self, set_id: SetId, rooms: list[Room]) -> None:
        self._rooms[set_id] = rooms

    def rooms_for(self, set_id: SetId) -> list[Room]:
        return list(self._rooms.get(set_id, []))

    def put_definitions(self, set_id: SetId, defs: list[WCDefinition]) -> None:
        self._definitions[set_id] = defs

    def put_applications(self, set_id: SetId, apps: list[Application]) -> None:
        self._applications[set_id] = apps

    def applications_for(self, set_id: SetId) -> list[Application]:
        return list(self._applications.get(set_id, []))

    def put_policy(self, set_id: SetId, policy: PolicySnapshot) -> None:
        self._policies[set_id] = policy

    def put_flags(self, set_id: SetId, flags: list[Flag]) -> None:
        self._flags[set_id] = flags

    # -- frozen interfaces ----------------------------------------------

    def save_project(self, set_id: SetId, dest: Path) -> Path:
        """save_project(set_id: SetId, dest: Path) -> Path

        Frozen interface SaveProject (NFR-2). Writes the entire project
        state for one drawing set to a single local SQLite file.
        """
        drawing_set = self._drawing_sets.get(set_id)
        if drawing_set is None:
            raise KeyError(f"unknown set_id {set_id!r}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()  # a save is a full snapshot, not a merge
        connection = sqlite3.connect(dest)
        try:
            connection.executescript(_schema_sql())
            self._write(connection, drawing_set)
            connection.commit()
        finally:
            connection.close()
        return dest

    def load_project(self, src: Path) -> SetId:
        """load_project(src: Path) -> SetId

        Frozen interface LoadProject (NFR-2): reload plus recompute must
        reproduce identical figures, which holds because every Decimal
        round-trips as verbatim TEXT and no value passes through float.
        """
        connection = sqlite3.connect(src)
        try:
            connection.row_factory = sqlite3.Row
            set_id = self._read(connection)
        finally:
            connection.close()
        return set_id

    # -- internals -------------------------------------------------------

    def _write(self, con: sqlite3.Connection, ds: DrawingSet) -> None:
        con.execute(
            "INSERT INTO drawing_set (set_id, project_name, created_at) "
            "VALUES (?, ?, ?)",
            (str(ds.set_id), ds.project_name, ds.created_at.isoformat()),
        )
        for sheet in ds.sheets:
            con.execute(
                "INSERT INTO sheet (sheet_id, set_id, path, role, "
                "sheet_number, thumbnail) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(sheet.sheet_id),
                    str(ds.set_id),
                    str(sheet.path),
                    sheet.role.value,
                    sheet.sheet_number,
                    sheet.thumbnail,
                ),
            )
        for defn in self._definitions.get(ds.set_id, []):
            con.execute(
                "INSERT INTO wc_definition (wc_tag, set_id, manufacturer, "
                "pattern_name, roll_width_in, repeat_in, match_type, "
                "unit_of_sale, yield_per_unit, source_sheet_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    defn.wc_tag,
                    str(ds.set_id),
                    _enc(defn.manufacturer),
                    _enc(defn.pattern_name),
                    _enc(defn.roll_width_in),
                    _enc(defn.repeat_in),
                    _enc(defn.match_type),
                    defn.unit_of_sale.value,
                    _enc(defn.yield_per_unit),
                    str(defn.source_sheet_id),
                ),
            )
        for room in self._rooms.get(ds.set_id, []):
            con.execute(
                "INSERT INTO room (room_id, set_id, room_number, "
                "ceiling_height_in, blanket_note) VALUES (?, ?, ?, ?, ?)",
                (
                    str(room.room_id),
                    str(ds.set_id),
                    room.room_number,
                    None
                    if room.ceiling_height_in is None
                    else str(room.ceiling_height_in),
                    room.blanket_note,
                ),
            )
            for wall in room.walls:
                con.execute(
                    "INSERT INTO wall (wall_id, room_id, orientation, "
                    "width_in, applied_height_in, manual_area_sf) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(wall.wall_id),
                        str(room.room_id),
                        wall.orientation,
                        None if wall.width_in is None else str(wall.width_in),
                        None
                        if wall.applied_height_in is None
                        else str(wall.applied_height_in),
                        None
                        if wall.manual_area_sf is None
                        else str(wall.manual_area_sf),
                    ),
                )
                for opening in wall.openings:
                    con.execute(
                        "INSERT INTO opening (opening_id, room_id, wall_id, "
                        "kind, width_in, height_in) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            str(opening.opening_id),
                            str(room.room_id),
                            str(wall.wall_id),
                            opening.kind,
                            str(opening.width_in),
                            str(opening.height_in),
                        ),
                    )
        for app in self._applications.get(ds.set_id, []):
            con.execute(
                "INSERT INTO application (application_id, set_id, wc_tag, "
                "room_id, wall_id, origin, source_sheet_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(app.application_id),
                    str(ds.set_id),
                    app.wc_tag,
                    str(app.room_id),
                    str(app.wall_id),
                    app.origin.value,
                    str(app.source_sheet_id),
                ),
            )
        policy = self._policies.get(ds.set_id)
        if policy is not None:
            con.execute(
                "INSERT INTO policy_snapshot (set_id, waste_pct, "
                "per_wc_waste_json, deduct_openings, opening_threshold_sf, "
                "trim_allowance_in) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(ds.set_id),
                    str(policy.waste_pct),
                    json.dumps(
                        {k: str(v) for k, v in policy.per_wc_waste.items()}
                    ),
                    1 if policy.deduct_openings else 0,
                    str(policy.opening_threshold_sf),
                    str(policy.trim_allowance_in),
                ),
            )
        for flag in self._flags.get(ds.set_id, []):
            con.execute(
                "INSERT INTO flag (flag_id, set_id, kind, subject_kind, "
                "subject_ref_id, source_sheet_id, blocks_json, detail, "
                "resolved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    str(flag.flag_id),
                    str(ds.set_id),
                    flag.kind.value,
                    flag.subject_ref.kind,
                    flag.subject_ref.ref_id,
                    None
                    if flag.source_sheet_id is None
                    else str(flag.source_sheet_id),
                    json.dumps(flag.blocks),
                    flag.detail,
                ),
            )

    def _read(self, con: sqlite3.Connection) -> SetId:
        ds_row = con.execute("SELECT * FROM drawing_set").fetchone()
        if ds_row is None:
            raise ValueError("project file contains no drawing set")
        set_id = SetId(ds_row["set_id"])
        sheets = [
            Sheet(
                sheet_id=SheetId(r["sheet_id"]),
                path=Path(r["path"]),
                role=SheetRole(r["role"]),
                sheet_number=r["sheet_number"],
                thumbnail=r["thumbnail"],
            )
            for r in con.execute(
                "SELECT * FROM sheet WHERE set_id = ?", (str(set_id),)
            )
        ]
        self._drawing_sets[set_id] = DrawingSet(
            set_id=set_id,
            project_name=ds_row["project_name"],
            sheets=sheets,
            created_at=_dt.datetime.fromisoformat(ds_row["created_at"]),
        )
        self._definitions[set_id] = [
            WCDefinition(
                wc_tag=r["wc_tag"],
                manufacturer=_dec_str(r["manufacturer"]),
                pattern_name=_dec_str(r["pattern_name"]),
                roll_width_in=_dec_decimal(r["roll_width_in"]),
                repeat_in=_dec_decimal(r["repeat_in"]),
                match_type=_dec_match(r["match_type"]),
                unit_of_sale=UnitOfSale(r["unit_of_sale"]),
                yield_per_unit=_dec_decimal(r["yield_per_unit"]),
                source_sheet_id=SheetId(r["source_sheet_id"]),
            )
            for r in con.execute(
                "SELECT * FROM wc_definition WHERE set_id = ?", (str(set_id),)
            )
        ]
        rooms: list[Room] = []
        for r in con.execute(
            "SELECT * FROM room WHERE set_id = ?", (str(set_id),)
        ):
            room_id = RoomId(r["room_id"])
            walls: list[Wall] = []
            for w in con.execute(
                "SELECT * FROM wall WHERE room_id = ?", (str(room_id),)
            ):
                openings = [
                    Opening(
                        opening_id=OpeningId(o["opening_id"]),
                        kind=o["kind"],
                        width_in=Decimal(o["width_in"]),
                        height_in=Decimal(o["height_in"]),
                    )
                    for o in con.execute(
                        "SELECT * FROM opening WHERE room_id = ? AND wall_id = ?",
                        (str(room_id), w["wall_id"]),
                    )
                ]
                walls.append(
                    Wall(
                        wall_id=WallId(w["wall_id"]),
                        room_id=room_id,
                        orientation=w["orientation"],
                        width_in=_opt_decimal(w["width_in"]),
                        applied_height_in=_opt_decimal(w["applied_height_in"]),
                        openings=openings,
                        manual_area_sf=_opt_decimal(w["manual_area_sf"]),
                    )
                )
            rooms.append(
                Room(
                    room_id=room_id,
                    room_number=r["room_number"],
                    ceiling_height_in=_opt_decimal(r["ceiling_height_in"]),
                    walls=walls,
                    blanket_note=r["blanket_note"],
                )
            )
        self._rooms[set_id] = rooms
        self._applications[set_id] = [
            Application(
                application_id=r["application_id"],
                wc_tag=r["wc_tag"],
                room_id=RoomId(r["room_id"]),
                wall_id=WallId(r["wall_id"]),
                origin=ApplicationOrigin(r["origin"]),
                source_sheet_id=SheetId(r["source_sheet_id"]),
            )
            for r in con.execute(
                "SELECT * FROM application WHERE set_id = ?", (str(set_id),)
            )
        ]
        p = con.execute(
            "SELECT * FROM policy_snapshot WHERE set_id = ?", (str(set_id),)
        ).fetchone()
        if p is not None:
            self._policies[set_id] = PolicySnapshot(
                waste_pct=Decimal(p["waste_pct"]),
                per_wc_waste={
                    k: Decimal(v)
                    for k, v in json.loads(p["per_wc_waste_json"]).items()
                },
                deduct_openings=bool(p["deduct_openings"]),
                opening_threshold_sf=Decimal(p["opening_threshold_sf"]),
                trim_allowance_in=Decimal(p["trim_allowance_in"]),
            )
        self._flags[set_id] = [
            Flag(
                flag_id=FlagId(r["flag_id"]),
                kind=FlagKind(r["kind"]),
                subject_ref=SubjectRef(
                    kind=r["subject_kind"], ref_id=r["subject_ref_id"]
                ),
                source_sheet_id=None
                if r["source_sheet_id"] is None
                else SheetId(r["source_sheet_id"]),
                blocks=json.loads(r["blocks_json"]),
                detail=r["detail"],
            )
            for r in con.execute(
                "SELECT * FROM flag WHERE set_id = ?", (str(set_id),)
            )
        ]
        return set_id


def _schema_sql() -> str:
    """The DDL shipped alongside this module (schema.sql)."""
    return (
        resources.files("wctakeoff.persistence")
        .joinpath("schema.sql")
        .read_text(encoding="utf-8")
    )


def new_project(project_name: str, sheets: list[Sheet]) -> DrawingSet:
    """Convenience constructor for a fresh DrawingSet (ARCH-A10)."""
    return DrawingSet(
        set_id=new_set_id(),
        project_name=project_name,
        sheets=sheets,
        created_at=_dt.datetime.now(tz=_dt.timezone.utc),
    )
