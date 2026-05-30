# ingestion/normalize.py
import re
from zoneinfo import ZoneInfo
from datetime import datetime
from ingestion.models import Event

MOUNTAIN = ZoneInfo("America/Denver")

def normalize_event(event: Event) -> Event:
    event.title = clean_title(event.title)
    event.venue_name = clean_venue_name(event.venue_name)
    event.venue_city = clean_city(event.venue_city)
    event.date = normalize_date(event.date)
    event.time = normalize_time(event.time)
    if event.genre:
        event.genre = event.genre.strip().title()
    return event

def clean_title(title: str) -> str:
    # Remove "presented by X" suffixes
    title = re.sub(r'\s*[-–]\s*presented by .+$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*\(presented by .+?\)', '', title, flags=re.IGNORECASE)
    # Remove excessive whitespace
    return " ".join(title.split()).strip()

def clean_venue_name(name: str) -> str:
    # Normalize common venue name variations
    replacements = {
        "Red Rocks Amphitheater": "Red Rocks Amphitheatre",
        "Red Rocks": "Red Rocks Amphitheatre",
        "Mission": "Mission Ballroom",
    }
    for old, new in replacements.items():
        if name.strip() == old:
            return new
    return name.strip()

def clean_city(city: str) -> str:
    city = city.strip()
    # Map common variants
    if city.lower() in ("denver, co", "denver co"):
        return "Denver"
    return city

def normalize_date(date_str: str) -> str:
    if not date_str:
        return ""
    # Handle ISO format with time component
    if "T" in date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            dt = dt.astimezone(MOUNTAIN)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return date_str[:10]

def normalize_time(time_str: str | None) -> str | None:
    if not time_str:
        return None
    # Accept HH:MM or HH:MM:SS
    match = re.match(r'(\d{2}):(\d{2})', time_str)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    return None