import json, sys
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import anthropic
from ingestion.db import get_connection

TM_AFFILIATE_ID = "DENVERBEATS"  # Replace with your real CJ affiliate ID when approved

def add_affiliate(url, affiliate_id=TM_AFFILIATE_ID):
    if not url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}camefrom={affiliate_id}"

def get_week_events(conn):
    today = date.today()
    week_end = today + timedelta(days=7)
    rows = conn.execute("""
        SELECT title, venue_name, venue_city, date, time,
               genre, artist_names, price_min, price_max,
               ticket_status, ticket_url, image_url
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
        d["ticket_url"] = add_affiliate(d["ticket_url"])
        events.append(d)
    return events

def format_price(price_min):
    if not price_min:
        return ""
    return f"${int(price_min)}+"

def format_date(date_str):
    from datetime import datetime
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%A, %B %-d")

def generate():
    conn = get_connection()
    events = get_week_events(conn)
    conn.close()

    if not events:
        print("No events found for this week")
        return

    print(f"Generating weekly digest for {len(events)} events...")

    client = anthropic.Anthropic()

    system = """You are the editor of Denver Beats, a curated weekly live music guide for Denver, Colorado.
Your readers are local music fans aged 25-45. Write like a knowledgeable friend, not a press release.
Be specific, enthusiastic but not breathless, and always local in perspective.
You must return ONLY valid HTML with no markdown, no backticks, no explanation — just the HTML fragment."""

    user = f"""Here is this week's event data:

{json.dumps(events, indent=2)}

Write a weekly digest as an HTML fragment (no <html>, <head>, or <body> tags).
Use this exact structure and styling:

<!-- HEADER -->
<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #1a1a1a;">

<!-- INTRO -->
<p style="font-size: 16px; color: #555; margin-bottom: 32px; line-height: 1.6;">
  [2-3 sentence intro about this week in Denver music. Be specific and local.]
</p>

<!-- SHOW OF THE WEEK -->
<div style="border-left: 4px solid #e8ff47; padding-left: 20px; margin-bottom: 32px; background: #fafafa; padding: 20px; border-radius: 8px;">
  <p style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #999; margin-bottom: 8px;">Show of the Week</p>
  <h2 style="font-size: 22px; font-weight: 700; margin: 0 0 8px;">[ARTIST NAME]</h2>
  <p style="font-size: 13px; color: #666; margin: 0 0 12px;">[VENUE] · [DATE] · [TIME] · [PRICE]</p>
  <p style="font-size: 15px; line-height: 1.7; margin: 0 0 16px;">[2-3 sentences on why this is the must-see show. Be specific.]</p>
  <a href="[TICKET_URL]" style="display: inline-block; background: #e8ff47; color: #000; font-weight: 700; font-size: 13px; padding: 10px 20px; border-radius: 6px; text-decoration: none;">Get tickets →</a>
</div>

<!-- DON'T MISS -->
<h3 style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #999; margin-bottom: 16px;">Don't Miss This Week</h3>

[Repeat this block 3-4 times for top picks:]
<div style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee;">
  <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
    <div>
      <p style="font-weight: 700; font-size: 16px; margin: 0 0 4px;">[ARTIST]</p>
      <p style="font-size: 13px; color: #666; margin: 0;">[VENUE] · [DATE] · [TIME]</p>
    </div>
    <div style="text-align: right;">
      [PRICE IF AVAILABLE]
      <a href="[TICKET_URL]" style="display: block; background: #1a1a1a; color: #fff; font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 4px; text-decoration: none; margin-top: 4px;">Tickets →</a>
    </div>
  </div>
  <p style="font-size: 14px; color: #444; margin: 10px 0 0; line-height: 1.6;">[1-2 sentences about why this show is worth it]</p>
</div>

<!-- FULL WEEK LISTINGS -->
<h3 style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #999; margin: 32px 0 16px;">Full Week Listings</h3>

<table style="width: 100%; border-collapse: collapse; font-size: 13px;">
  <thead>
    <tr style="border-bottom: 2px solid #eee;">
      <th style="text-align: left; padding: 8px 4px; color: #999; font-weight: 600;">Show</th>
      <th style="text-align: left; padding: 8px 4px; color: #999; font-weight: 600;">Venue</th>
      <th style="text-align: left; padding: 8px 4px; color: #999; font-weight: 600;">Date</th>
      <th style="text-align: right; padding: 8px 4px; color: #999; font-weight: 600;">Price</th>
      <th style="text-align: right; padding: 8px 4px;"></th>
    </tr>
  </thead>
  <tbody>
    [For EVERY event, add a row:]
    <tr style="border-bottom: 1px solid #f0f0f0;">
      <td style="padding: 10px 4px; font-weight: 500;">[ARTIST/SHOW]</td>
      <td style="padding: 10px 4px; color: #666;">[VENUE]</td>
      <td style="padding: 10px 4px; color: #666;">[DAY, DATE · TIME]</td>
      <td style="padding: 10px 4px; text-align: right; color: #2a7a2a; font-weight: 600;">[PRICE OR —]</td>
      <td style="padding: 10px 4px; text-align: right;"><a href="[TICKET_URL]" style="color: #000; font-weight: 600; font-size: 12px; text-decoration: none; background: #f0f0f0; padding: 4px 10px; border-radius: 4px;">Tickets</a></td>
    </tr>
  </tbody>
</table>

<!-- HIDDEN GEM -->
<div style="background: #f8f4ff; border-radius: 8px; padding: 20px; margin: 32px 0;">
  <p style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #9b59b6; margin-bottom: 8px;">Hidden Gem</p>
  <p style="font-weight: 700; font-size: 16px; margin: 0 0 4px;">[ARTIST] @ [SMALL VENUE]</p>
  <p style="font-size: 13px; color: #666; margin: 0 0 12px;">[DATE · TIME · PRICE]</p>
  <p style="font-size: 14px; line-height: 1.7; margin: 0 0 12px;">[Why this under-the-radar show is worth it]</p>
  <a href="[TICKET_URL]" style="font-size: 13px; font-weight: 600; color: #9b59b6; text-decoration: none;">Get tickets →</a>
</div>

<!-- UNDER $20 -->
<h3 style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #999; margin: 32px 0 16px;">Under $20 This Week</h3>
<ul style="list-style: none; padding: 0; margin: 0;">
  [3-5 affordable shows:]
  <li style="padding: 10px 0; border-bottom: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center;">
    <div>
      <span style="font-weight: 600; font-size: 14px;">[ARTIST]</span>
      <span style="color: #666; font-size: 13px;"> @ [VENUE] · [DATE]</span>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
      <span style="color: #2a7a2a; font-weight: 700; font-size: 13px;">[PRICE]</span>
      <a href="[TICKET_URL]" style="font-size: 12px; font-weight: 600; color: #000; text-decoration: none; background: #e8ff47; padding: 4px 10px; border-radius: 4px;">Tickets</a>
    </div>
  </li>
</ul>

<!-- FOOTER -->
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
  <p>Denver Beats — updated daily</p>
  <p style="margin-top: 4px;">Event data via <a href="https://ticketmaster.com" style="color: #999;">Ticketmaster</a> · <a href="https://denver-beats.pages.dev" style="color: #999;">View full listings</a></p>
</div>

</div>

CRITICAL RULES:
- Use the EXACT ticket_url values from the event data for every single link — do not modify them
- Include ALL events in the Full Week Listings table — every single one
- Only include shows with ticket_status != cancelled
- If price_min is null, show — in the price column
- Never invent details not in the data
- Return ONLY the HTML, nothing else, no explanation, no backticks"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user}]
    )

    digest_html = message.content[0].text
    week_str = date.today().strftime("%Y-W%W")

    out_path = Path(f"data/digests/weekly/{week_str}.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(digest_html)

    md_path = Path(f"data/digests/weekly/{week_str}.md")
    md_path.write_text(digest_html)

    print(f"Weekly digest written to {out_path}")
    print(f"Tokens used: {message.usage.input_tokens} in / {message.usage.output_tokens} out")
    print(f"\nOpen the file and copy the HTML into Substack:")
    print(f"  open {out_path}")

if __name__ == "__main__":
    generate()
