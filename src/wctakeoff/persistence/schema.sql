-- wallcovering-takeoff project persistence schema.
-- Requirement ids: NFR-2 (ADR-001: ProjectRepository is the only
-- persistence boundary; ARCH-A10: one project file, no multi-tenant state).
--
-- All Decimal values are stored as TEXT verbatim so reload plus recompute
-- reproduces byte-identical figures (NFR-2); nothing is stored as float.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS drawing_set (
    set_id       TEXT PRIMARY KEY,
    project_name TEXT NOT NULL CHECK (length(project_name) > 0),
    created_at   TEXT NOT NULL  -- ISO-8601 UTC, set once
);

CREATE TABLE IF NOT EXISTS sheet (
    sheet_id     TEXT PRIMARY KEY,
    set_id       TEXT NOT NULL REFERENCES drawing_set(set_id),
    path         TEXT NOT NULL,
    role         TEXT NOT NULL CHECK (role IN
        ('SCHEDULE','FINISH_PLAN','CEILING_HEIGHT_PLAN','ELEVATION','UNASSIGNED')),
    sheet_number TEXT,
    thumbnail    BLOB NOT NULL DEFAULT X''
);

CREATE TABLE IF NOT EXISTS wc_definition (
    wc_tag          TEXT PRIMARY KEY CHECK (wc_tag IN ('WC-1','WC-2','WC-3')),
    set_id          TEXT NOT NULL REFERENCES drawing_set(set_id),
    -- SET READ fields stored verbatim; the literal 'UNKNOWN' encodes the
    -- sentinel (ADR-002). Never a default, never an imputed value.
    manufacturer    TEXT NOT NULL,
    pattern_name    TEXT NOT NULL,
    roll_width_in   TEXT NOT NULL,
    repeat_in       TEXT NOT NULL,
    match_type      TEXT NOT NULL CHECK (match_type IN
        ('STRAIGHT','HALF_DROP','RANDOM','UNKNOWN')),
    unit_of_sale    TEXT NOT NULL CHECK (unit_of_sale IN ('LINEAR_YARD','ROLL')),
    yield_per_unit  TEXT NOT NULL,
    source_sheet_id TEXT NOT NULL REFERENCES sheet(sheet_id)
);

CREATE TABLE IF NOT EXISTS room (
    room_id           TEXT PRIMARY KEY,
    set_id            TEXT NOT NULL REFERENCES drawing_set(set_id),
    room_number       TEXT NOT NULL CHECK (length(room_number) > 0),
    ceiling_height_in TEXT,          -- NULL blocks area derivation (ADR-005)
    blanket_note      TEXT
);

CREATE TABLE IF NOT EXISTS wall (
    wall_id           TEXT NOT NULL,
    room_id           TEXT NOT NULL REFERENCES room(room_id),
    orientation       TEXT NOT NULL DEFAULT '',
    width_in          TEXT,
    applied_height_in TEXT,
    manual_area_sf    TEXT,          -- ARCH-A11 escape hatch; requires flag
    PRIMARY KEY (room_id, wall_id)   -- de-duplication identity (ADR-009)
);

CREATE TABLE IF NOT EXISTS opening (
    opening_id TEXT PRIMARY KEY,
    room_id    TEXT NOT NULL,
    wall_id    TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'OTHER',
    width_in   TEXT NOT NULL,
    height_in  TEXT NOT NULL,
    FOREIGN KEY (room_id, wall_id) REFERENCES wall(room_id, wall_id)
);

CREATE TABLE IF NOT EXISTS application (
    application_id  TEXT PRIMARY KEY,
    set_id          TEXT NOT NULL REFERENCES drawing_set(set_id),
    wc_tag          TEXT NOT NULL,
    room_id         TEXT NOT NULL,
    wall_id         TEXT NOT NULL,
    origin          TEXT NOT NULL CHECK (origin IN
        ('ROOM_BLANKET','WALL_OVERRIDE','ELEVATION_TAG')),
    source_sheet_id TEXT NOT NULL REFERENCES sheet(sheet_id),
    UNIQUE (wc_tag, room_id, wall_id),
    FOREIGN KEY (room_id, wall_id) REFERENCES wall(room_id, wall_id)
);

CREATE TABLE IF NOT EXISTS policy_snapshot (
    set_id               TEXT PRIMARY KEY REFERENCES drawing_set(set_id),
    waste_pct            TEXT NOT NULL,
    per_wc_waste_json    TEXT NOT NULL DEFAULT '{}',
    deduct_openings      INTEGER NOT NULL DEFAULT 1,
    opening_threshold_sf TEXT NOT NULL,
    trim_allowance_in    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flag (
    flag_id         TEXT PRIMARY KEY,
    set_id          TEXT NOT NULL REFERENCES drawing_set(set_id),
    kind            TEXT NOT NULL CHECK (kind IN
        ('UNKNOWN_SCHEDULE_FIELD','MISSING_HEIGHT','UNRESOLVED_UNO',
         'UNDEFINED_WC','UNUSED_WC','CONFLICT','UNREADABLE_DIMENSION',
         'NON_RECTANGULAR','UNKNOWN_MATCH_TYPE')),
    subject_kind    TEXT NOT NULL,
    subject_ref_id  TEXT NOT NULL,
    source_sheet_id TEXT REFERENCES sheet(sheet_id),
    blocks_json     TEXT NOT NULL DEFAULT '[]',
    detail          TEXT NOT NULL CHECK (length(detail) > 0),
    resolved        INTEGER NOT NULL DEFAULT 0
);
