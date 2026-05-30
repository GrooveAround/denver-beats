import os, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ingestion.models import Event
from ingestion.config import FETCH_DAYS_AHEAD

MOUNTAIN = ZoneInfo("America/Denver")
TM_BASE  = "https://app.ticketmaster.com/discovery/v2"

VENUE_NAME_OVERRIDES = {
    "KovZpZA7AAEA": "Red Rocks Amphitheatre",
}

SEARCH_TARGETS = [
    ("Denver",   "CO"),
    ("Boulder",  "CO"),
    ("Morrison", "CO"),
    ("Golden",   "CO"),
]

def fetch_events(days_ahead=FETCH_DAYS_AHEAD):
    api_key = os.environ.get("TM_API_KEY", "")
    if not api_key:
        print("[TM] No API key found, skipping")
        return []

    now   = datetime.now(MOUNTAIN)
    start = now.strftime("%Y-%m-%dT00:00:00Z")
    end   = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT23:59:59Z")

    seen_ids   = set()
    all_events = []

    for city, state in SEARCH_TARGETS:
        page = 0
        while True:
            params = {
                "apikey":             api_key,
                "city":               city,
                "stateCode":          state,
                "classificationName": "Music",
                "startDateTime":      start,
                "endDateTime":        end,
                "size":               200,
                "page":               page,
                "sort":               "date,asc",
                "locale":             "*",
            }
            try:
                resp = requests.get(f"{TM_BASE}/events.json", params=params, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[TM] Request failed ({city}, page {page}): {e}")
                break

            items = data.get("_embedded", {}).get("events", [])
            if not items:
                break

            for item in items:
                tm_id = item.get("id", "")
                if tm_id in seen_ids:
                    continue
                seen_ids.add(tm_id)
                event = _parse_event(item)
                if event:
                    all_events.append(event)

            total_pages = data.get("page", {}).get("totalPages", 1)
            page += 1
            if page >= total_pages or page > 10:
                break

    print(f"[TM] Fetched {len(all_events)} events")
    return all_events


def _parse_event(item):
    try:
        venues     = item.get("_embedded", {}).get("venues", [{}])
        venue_data = venues[0] if venues else {}
        venue_id   = venue_data.get("id", "")
        venue_name = VENUE_NAME_OVERRIDES.get(venue_id, venue_data.get("name", "Unknown Venue"))
        city       = venue_data.get("city", {}).get("name", "Denver")

        date_info = item.get("dates", {}).get("start", {})
        date      = date_info.get("localDate", "")
        time      = (date_info.get("localTime", "") or "")[:5] or None
        if not date:
            return None

        ticket_url = item.get("url", "")
        if not ticket_url:
            return None

        price_min = price_max = None
        for pr in item.get("priceRanges", []):
            price_min = pr.get("min")
            price_max = pr.get("max")
            break

        status_map = {"onsale": "available", "offsale": "sold_out",
                      "cancelled": "cancelled", "rescheduled": "rescheduled"}
        raw_status = item.get("dates", {}).get("status", {}).get("code", "unknown")
        status     = status_map.get(raw_status, "unknown")

        genre_parts = []
        for c in item.get("classifications", []):
            for key in ("genre", "subGenre"):
                name = c.get(key, {}).get("name", "")
                if name and name.lower() not in ("undefined", "", "other"):
                    genre_parts.append(name)
        genre = " / ".join(dict.fromkeys(genre_parts)) or None

        artists = [a.get("name", "") for a in
                   item.get("_embedded", {}).get("attractions", []) if a.get("name")]

        images    = sorted([img for img in item.get("images", [])
                            if img.get("ratio") == "16_9"],
                           key=lambda x: x.get("width", 0), reverse=True)
        image_url = images[0]["url"] if images else None

        return Event(
            title=item.get("name", "Untitled"),
            venue_name=venue_name,
            venue_city=city,
            date=date,
            time=time,
            ticket_url=ticket_url,
            source="ticketmaster",
            source_event_id=item.get("id", ""),
            genre=genre,
            artist_names=artists,
            price_min=price_min,
            price_max=price_max,
            ticket_status=status,
            image_url=image_url,
        )
    except Exception as e:
        print(f"[TM] Parse error: {e}")
        return None
