# ingestion/models.py
from dataclasses import dataclass, field
from typing import Optional
import re, hashlib

@dataclass
class Event:
    title: str
    venue_name: str
    venue_city: str
    date: str                    # YYYY-MM-DD
    ticket_url: str
    source: str
    source_event_id: str

    time: Optional[str] = None   # HH:MM 24-hour
    doors_time: Optional[str] = None
    genre: Optional[str] = None
    artist_names: list = field(default_factory=list)
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    ticket_status: str = "unknown"
    image_url: Optional[str] = None
    age_restriction: Optional[str] = None
    description: Optional[str] = None

    @property
    def id(self) -> str:
        venue_slug = re.sub(r'[^a-z0-9]', '', self.venue_name.lower())
        title_slug = re.sub(r'[^a-z0-9]', '', self.title.lower())
        raw = f"{venue_slug}|{title_slug}|{self.date[:10]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "venue_name": self.venue_name,
            "venue_city": self.venue_city,
            "date": self.date,
            "time": self.time,
            "doors_time": self.doors_time,
            "genre": self.genre,
            "artist_names": self.artist_names,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "ticket_status": self.ticket_status,
            "ticket_url": self.ticket_url,
            "image_url": self.image_url,
            "age_restriction": self.age_restriction,
            "description": self.description,
            "source": self.source,
            "source_event_id": self.source_event_id,
        }