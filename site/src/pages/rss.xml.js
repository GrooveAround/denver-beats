// site/src/pages/rss.xml.js
import rss from '@astrojs/rss';
import { readFileSync } from 'fs';
import { resolve } from 'path';

export async function GET(context) {
  const eventsPath = resolve('../data/events.json');
  let events = [];
  try {
    events = JSON.parse(readFileSync(eventsPath, 'utf-8'));
  } catch (e) {
    events = [];
  }

  const today = new Date().toISOString().split('T')[0];
  const upcoming = events
    .filter(e => e.date >= today)
    .slice(0, 50);

  return rss({
    title: 'Little Get Around — Live Music Guide',
    description: 'Daily live music listings for Denver, Boulder, Red Rocks, and beyond.',
    site: context.site || 'https://YOUR_DOMAIN.com',
    items: upcoming.map(event => ({
      title: `${event.title} @ ${event.venue_name}`,
      pubDate: new Date(event.date + 'T12:00:00'),
      description: [
        `<strong>${event.date}</strong>`,
        event.time ? `Doors/Show: ${event.time}` : '',
        `Venue: ${event.venue_name}, ${event.venue_city}`,
        event.genre ? `Genre: ${event.genre}` : '',
        event.price_min ? `Starting at $${Math.round(event.price_min)}` : '',
        event.ticket_status === 'sold_out' ? '<em>SOLD OUT</em>' : '',
        `<a href="${event.ticket_url}">Get tickets →</a>`,
      ].filter(Boolean).join('<br/>'),
      link: event.ticket_url,
      guid: event.id,
    })),
  });
}