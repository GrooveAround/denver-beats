# ingestion/config.py
from dataclasses import dataclass

DENVER_METRO_CITIES = [
    "Denver", "Boulder", "Morrison", "Golden",
    "Englewood", "Lakewood", "Aurora", "Arvada",
    "Westminster", "Broomfield", "Littleton"
]

# Ticketmaster DMA IDs for the Denver metro area
TM_DMA_IDS = ["323"]  # Denver DMA

# How many days ahead to fetch
FETCH_DAYS_AHEAD = 60

# Source priority (lower = more trusted, wins dedup)
SOURCE_PRIORITY = {
    "ticketmaster": 1,
    "eventbrite":   2,
    "red_rocks":    3,
}

@dataclass
class VenueConfig:
    name: str
    city: str
    tm_id: str = ""

KNOWN_VENUES = [
    VenueConfig("Red Rocks Amphitheatre",  "Morrison",  "KovZpZA7AAEA"),
    VenueConfig("Ball Arena",              "Denver",    "KovZpZAde1d"),
    VenueConfig("Fiddler's Green",         "Greenwood Village"),
    VenueConfig("Mission Ballroom",        "Denver"),
    VenueConfig("Ogden Theatre",           "Denver"),
    VenueConfig("Bluebird Theater",        "Denver"),
    VenueConfig("Globe Hall",              "Denver"),
    VenueConfig("Larimer Lounge",          "Denver"),
    VenueConfig("Boulder Theater",         "Boulder"),
    VenueConfig("Fox Theatre",             "Boulder"),
    VenueConfig("Summit Music Hall",       "Denver"),
    VenueConfig("Fillmore Auditorium",     "Denver"),
    VenueConfig("Levitt Pavilion",         "Denver"),
]