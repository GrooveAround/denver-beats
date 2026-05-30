# ingestion/fetchers/red_rocks.py
"""
Red Rocks events scraper.
Red Rocks is a City of Denver venue. Their event calendar is public.
We check robots.txt — it does not disallow /events/.
Rate limiting: one request per day in production.
"""
import requests
from bs4 import BeautifulSoup
from ingestion.models import Event

HEADERS = {
    "User-Agent": "DenverBeats-Bot/1.0 (+https://denverbeats.com/bot)"
}

def fetch_events() -> list[Event]:
    """
    Red Rocks posts events at their official page.
    We also check the Ticketmaster-powered listings, which is the primary source.
    This scraper acts as a cross-reference.
    """
    events = []

    try:
        url = "https://www.redrocksonline.com/events/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Red Rocks uses a card-based layout. Each event is in an article or div.
        # This selector may need updating if the site redesigns.
        event_cards = soup.select(".event-card, .events-list__item, article.event")

        for card in event_cards:
            try:
                title_el = card.select_one("h2, h3, .event-title, .event-name")
                date_el  = card.select_one(".event-date, time, [datetime]")
                link_el  = card.select_one("a[href]")

                if not all([title_el, date_el, link_el]):
                    continue

                title = title_el.get_text(strip=True)
                date_raw = (date_el.get("datetime") or date_el.get_text(strip=True))
                link = link_el["href"]
                if not link.startswith("http"):
                    link = "https://www.redrocksonline.com" + link

                date = _parse_date(date_raw)
                if not date:
                    continue

                events.append(Event(
                    title=title,
                    venue_name="Red Rocks Amphitheatre",
                    venue_city="Morrison",
                    date=date,
                    ticket_url=link,
                    source="red_rocks",
                    source_event_id=link.split("/")[-2],
                ))
            except Exception as e:
                print(f"[RR] Card parse error: {e}")
                continue

    except Exception as e:
        print(f"[RR] Scrape failed: {e}")

    print(f"[RR] Fetched {len(events)} events")
    return events


def _parse_date(raw: str) -> str | None:
    from datetime import datetime
    formats = ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"]
    raw = raw.strip()[:20]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None