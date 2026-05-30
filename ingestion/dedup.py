# ingestion/dedup.py
import sqlite3
from rapidfuzz import fuzz
from ingestion.db import get_events_in_window

SIMILARITY_THRESHOLD = 85  # percent

def find_duplicate(event, conn: sqlite3.Connection) -> str | None:
    """
    Returns the canonical event ID if a duplicate is found, else None.
    """
    candidates = get_events_in_window(conn, event.venue_name, event.date)
    for candidate in candidates:
        similarity = fuzz.token_sort_ratio(
            event.title.lower(),
            candidate["title"].lower()
        )
        if similarity >= SIMILARITY_THRESHOLD:
            print(f"  [dedup] '{event.title}' matches '{candidate['title']}' "
                  f"({similarity}%) → duplicate of {candidate['id']}")
            return candidate["id"]
    return None