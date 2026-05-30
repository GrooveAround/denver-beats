# digest/generate_weekly.py
"""
Generates the weekly digest. Run every Friday.
Usage: python digest/generate_weekly.py
"""
import json, sys
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import anthropic
from ingestion.db import get_connection

def get_week_events(conn):
    today = date.today()
    week_end = today + timedelta(days=7)
    rows = conn.execute("""
        SELECT title, venue_name, venue_city, date, time,
               genre, artist_names, price_min, price_max,
               ticket_status, ticket_url
        FROM events
        WHERE is_duplicate = 0
          AND date BETWEEN ? AND ?
        ORDER BY date ASC, time ASC
    """, (today.isoformat(), week_end.isoformat())).fetchall()
    events = []
    for row in rows:
        d = dict(row)
        try:
            d["artist_names"] = json.loads(d["artist_names"] or "[]")
        except Exception:
            d["artist_names"] = []
        events.append(d)
    return events

def generate():
    conn = get_connection()
    events = get_week_events(conn)
    conn.close()

    if not events:
        print("No events found for this week")
        return

    print(f"Generating weekly digest for {len(events)} events...")

    from digest.prompts import WEEKLY_SYSTEM, WEEKLY_USER
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=WEEKLY_SYSTEM,
        messages=[{
            "role": "user",
            "content": WEEKLY_USER.format(
                events_json=json.dumps(events, indent=2)
            )
        }]
    )

    digest_text = message.content[0].text
    week_str = date.today().strftime("%Y-W%W")

    out_path = Path(f"data/digests/weekly/{week_str}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(f"---\ndate: {date.today().isoformat()}\nperiod: {week_str}\n---\n\n{digest_text}")

    print(f"Weekly digest written to {out_path}")
    print(f"Tokens used: {message.usage.input_tokens} in / {message.usage.output_tokens} out")

if __name__ == "__main__":
    generate()