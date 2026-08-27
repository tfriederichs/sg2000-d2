import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

TEAM_ID = "011MIENCLK000000VTVG0001VTR8C1K7"
TZ = ZoneInfo("Europe/Berlin")
OUT = Path("public/spielplan.ics")
SEASON_END = "2027-06-30"
SOURCE = f"https://www.fussball.de/mannschaft/sg-2000-muelheim-kaerlich-ii-sg-2000-muelheim-kaerlich-rheinland/-/saison/2627/team-id/{TEAM_ID}"

URL = (
    "https://www.fussball.de/ajax.team.matchplan/-/"
    "mime-type/JSON/mode/PAGE/prev-season-allowed/false/"
    "show-filter/false/show-venues/true/"
    f"team-id/{TEAM_ID}"
)

def esc(s):
    return str(s or "").replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")

def fetch():
    today = datetime.now(TZ).date().isoformat()
    r = requests.get(
        URL + f"/datum-von/{today}/datum-bis/{SEASON_END}/max/1000",
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json,text/plain,*/*"},
        timeout=60
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success") or not data.get("html"):
        raise RuntimeError("FUSSBALL.DE hat keine verwertbaren Daten geliefert.")
    return data["html"]

def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    games = {}
    for row in soup.select("tr"):
        clubs = row.select(".column-club .club-name")
        date_cell = row.select_one(".column-date")
        if len(clubs) < 2 or not date_cell:
            continue
        a = row.select_one(".column-score a[href*='/spiel/']")
        if not a:
            continue
        text = " ".join(date_cell.stripped_strings)
        m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4}).*?(\d{1,2}):(\d{2})", text)
        if not m:
            continue
        d, mo, y, h, mi = map(int, m.groups())
        if y < 100: y += 2000
        start = datetime(y, mo, d, h, mi, tzinfo=TZ)
        if start < datetime.now(TZ): continue

        href = a.get("href","")
        mid = re.search(r"/spiel/([^/]+)", href)
        uid = mid.group(1) if mid else f"{start.isoformat()}-{clubs[0].get_text(strip=True)}-{clubs[1].get_text(strip=True)}"

        venue = ""
        vr = row.find_next_sibling("tr", class_="row-venue")
        if vr:
            cells = vr.find_all("td")
            if len(cells) >= 2:
                venue = " ".join(cells[1].stripped_strings)

        games[uid] = {
            "id": uid, "start": start,
            "home": " ".join(clubs[0].stripped_strings),
            "away": " ".join(clubs[1].stripped_strings),
            "location": venue,
            "url": "https://www.fussball.de" + href if href.startswith("/") else href
        }
    return sorted(games.values(), key=lambda x:x["start"])

def fold(line):
    out=[]; cur=""
    for ch in line:
        if len((cur+ch).encode("utf-8")) > 75:
            out.append(cur); cur=" "+ch
        else: cur += ch
    if cur: out.append(cur)
    return out

def write(games):
    lines = [
        "BEGIN:VCALENDAR","VERSION:2.0",
        "PRODID:-//tfriederichs//SG 2000 D2//DE",
        "CALSCALE:GREGORIAN","METHOD:PUBLISH",
        "X-WR-CALNAME:SG 2000 Mülheim-Kärlich D2",
        "X-WR-TIMEZONE:Europe/Berlin"
    ]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for g in games:
        s=g["start"]; e=s+timedelta(hours=2)
        lines += [
            "BEGIN:VEVENT", f"UID:{esc(TEAM_ID+'-'+g['id']+'@github')}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=Europe/Berlin:{s:%Y%m%dT%H%M%S}",
            f"DTEND;TZID=Europe/Berlin:{e:%Y%m%dT%H%M%S}",
            f"SUMMARY:{esc(g['home']+' - '+g['away'])}",
            f"LOCATION:{esc(g['location'])}",
            f"DESCRIPTION:{esc('SG 2000 Mülheim-Kärlich D2\\nQuelle: FUSSBALL.DE\\n'+g['url'])}",
            f"URL:{g['url']}", "STATUS:CONFIRMED","TRANSP:OPAQUE","END:VEVENT"
        ]
    lines.append("END:VCALENDAR")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\r\n".join(x for line in lines for x in fold(line))+"\r\n", encoding="utf-8")

def main():
    games=parse(fetch())
    if not games and OUT.exists():
        print("Keine Spiele gefunden – vorhandenen Kalender behalten.")
        return
    if not games: raise RuntimeError("Keine zukünftigen Spiele gefunden.")
    write(games)
    print(f"{len(games)} zukünftige Spiele geschrieben.")
    for g in games: print(g["start"].strftime("%d.%m.%Y %H:%M"), g["home"], "-", g["away"], "|", g["location"])

if __name__ == "__main__":
    main()
