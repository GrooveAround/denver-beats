# ingestion/run_ingestion.py
"""
Main ingestion entry point. Run this daily.
Usage: python -m ingestion.run_ingestion
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present (for local development)
load_dotenv()

from ingestion.db import get_connection, init_db, upsert_event, export_json
from ingestion.normalize import normalize_event
from ingestion.dedup import find_duplicate
from ingestion.fetchers import ticketmaster, eventbrite, red_rocks
from ingestion.config import SOURCE_PRIORITY

FETCHERS = [
    (ticketmaster.fetch_events, SOURCE_PRIORITY["ticketmaster"]),
    (eventbrite.fetch_events,   SOURCE_PRIORITY["eventbrite"]),
    (red_rocks.fetch_events,    SOURCE_PRIORITY["red_rocks"]),
]

def run():
    print("=== Denver Beats Ingestion ===")
    conn = get_connection()
    init_db(conn)

    # Fetch from all sources
    all_events = []
    for fetcher_fn, priority in FETCHERS:
        source_name = fetcher_fn.__module__.split(".")[-1]
        print(f"\n--- Fetching from {source_name} ---")
        try:
            events = fetcher_fn()
            all_events.extend([(e, priority) for e in events])
        except Exception as ex:
            print(f"[ERROR] {source_name} failed: {ex}")

    # Sort by priority (lower number = more trusted, processed first)
    all_events.sort(key=lambda x: x[1])

    inserted = updated = duped = skipped = 0

    for event, priority in all_events:
        try:
            normalized = normalize_event(event)

            # Skip events without a date
            if not normalized.date:
                skipped += 1
                continue

            # Check for duplicates (only if not the top-priority source)
            canonical_id = None
            is_dup = False
            if priority > 1:
                canonical_id = find_duplicate(normalized, conn)
                if canonical_id:
                    is_dup = True
                    duped += 1

            upsert_event(conn, normalized,
                         is_duplicate=is_dup, canonical_id=canonical_id)

            if is_dup:
                pass  # already counted
            else:
                inserted += 1

        except Exception as ex:
            print(f"[ERROR] Processing event '{event.title}': {ex}")

    conn.commit()

    # Export JSON for the static site
    print("\n--- Exporting JSON ---")
    export_json(conn)

    conn.close()

    print(f"\n=== Done ===")
    print(f"  Canonical events written: {inserted}")
    print(f"  Duplicates flagged:       {duped}")
    print(f"  Skipped (no date):        {skipped}")
    return 0

if __name__ == "__main__":
    sys.exit(run())