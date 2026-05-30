# ingestion/db.py
import sqlite3, json
from pathlib import Path
from ingestion.models import Event

DB_PATH = Path("data/events.db")
JSON_PATH = Path("data/events.json")

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            venue_name      TEXT NOT NULL,
            venue_city      TEXT NOT NULL,
            date            TEXT NOT NULL,
            time            TEXT,
            doors_time      TEXT,
            artist_names    TEXT,
            genre           TEXT,
            description     TEXT,
            ticket_url      TEXT NOT NULL,
            ticket_status   TEXT DEFAULT 'unknown',
            age_restriction TEXT,
            source          TEXT NOT NULL,
            source_event_id TEXT,
            price_min       REAL,
            price_max       REAL,
            image_url       TEXT,
            is_duplicate    INTEGER DEFAULT 0,
            canonical_id    TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS price_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    TEXT NOT NULL,
            price_min   REAL,
            price_max   REAL,
            snapshot_at TEXT DEFAULT (datetime('now')),
            source      TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
        CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_name);
        CREATE INDEX IF NOT EXISTS idx_events_nodup ON events(is_duplicate);
    """)
    conn.commit()

def upsert_event(conn: sqlite3.Connection, event: Event,
                 is_duplicate: bool = False, canonical_id: str = None):
    d = event.to_dict()
    conn.execute("""
        INSERT INTO events (
            id, title, venue_name, venue_city, date, time, doors_time,
            artist_names, genre, description, ticket_url, ticket_status,
            age_restriction, source, source_event_id, price_min, price_max,
            image_url, is_duplicate, canonical_id, updated_at
        ) VALUES (
            :id, :title, :venue_name, :venue_city, :date, :time, :doors_time,
            :artist_names, :genre, :description, :ticket_url, :ticket_status,
            :age_restriction, :source, :source_event_id, :price_min, :price_max,
            :image_url, :is_duplicate, :canonical_id, datetime('now')
        )
        ON CONFLICT(id) DO UPDATE SET
            ticket_status   = excluded.ticket_status,
            price_min       = excluded.price_min,
            price_max       = excluded.price_max,
            image_url       = excluded.image_url,
            is_duplicate    = excluded.is_duplicate,
            canonical_id    = excluded.canonical_id,
            updated_at      = datetime('now')
    """, {
        **d,
        "artist_names": json.dumps(d["artist_names"]),
        "is_duplicate": 1 if is_duplicate else 0,
        "canonical_id": canonical_id,
    })

    # Record price snapshot if price is present
    if event.price_min is not None:
        conn.execute("""
            INSERT INTO price_snapshots (event_id, price_min, price_max, source)
            VALUES (?, ?, ?, ?)
        """, (event.id, event.price_min, event.price_max, event.source))

def get_events_in_window(conn: sqlite3.Connection, venue_name: str,
                         date: str, window_days: int = 1) -> list:
    from datetime import datetime, timedelta
    d = datetime.strptime(date[:10], "%Y-%m-%d")
    start = (d - timedelta(days=window_days)).strftime("%Y-%m-%d")
    end   = (d + timedelta(days=window_days)).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT id, title, venue_name, date, source
        FROM events
        WHERE venue_name LIKE ?
          AND date BETWEEN ? AND ?
          AND is_duplicate = 0
    """, (f"%{venue_name[:10]}%", start, end)).fetchall()
    return [dict(r) for r in rows]

def export_json(conn: sqlite3.Connection):
    """Export all non-duplicate future events to JSON for the static site."""
    from datetime import date
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT * FROM events
        WHERE is_duplicate = 0
          AND date >= ?
        ORDER BY date ASC, time ASC
    """, (today,)).fetchall()

    events = []
    for row in rows:
        d = dict(row)
        try:
            d["artist_names"] = json.loads(d["artist_names"] or "[]")
        except Exception:
            d["artist_names"] = []
        events.append(d)

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(events, indent=2))
    print(f"Exported {len(events)} events to {JSON_PATH}")