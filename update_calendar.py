import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


TEAM_ID = "011MIENCLK000000VTVG0001VTR8C1K7"

TZ = ZoneInfo("Europe/Berlin")

OUTPUT = Path("public/spielplan.ics")

SEASON_END = "2027-06-30"

SOURCE_URL = (
    "https://www.fussball.de/mannschaft/"
    "sg-2000-muelheim-kaerlich-ii-sg-2000-muelheim-kaerlich-rheinland/"
    "-/saison/2627/"
    f"team-id/{TEAM_ID}"
)

BASE_URL = (
    "https://www.fussball.de/ajax.team.matchplan/-/"
    "mime-type/JSON/mode/PAGE/"
    "prev-season-allowed/false/"
    "show-filter/false/"
    "show-venues/true/"
    f"team-id/{TEAM_ID}"
)


def escape(value):
    """Zeichen für das iCalendar-Format maskieren."""
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold_ics_line(line):
    """Zeilen gemäß iCalendar-Standard umbrechen."""
    result = []
    current = ""

    for char in line:
        candidate = current + char

        if len(candidate.encode("utf-8")) > 75:
            result.append(current)
            current = " " + char
        else:
            current = candidate

    if current:
        result.append(current)

    return result


def get_fussball_data():
    """Spielplan direkt von FUSSBALL.DE laden."""

    today = datetime.now(TZ).date().isoformat()

    url = (
        BASE_URL
        + f"/datum-von/{today}"
        + f"/datum-bis/{SEASON_END}"
        + "/max/1000"
    )

    print("FUSSBALL.DE wird abgefragt...")
    print(url)

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/139 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "de-DE,de;q=0.9",
        },
        timeout=60,
    )

    print("HTTP-Status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(
            "FUSSBALL.DE meldet success=false."
        )

    html = data.get("html", "")

    if not html:
        raise RuntimeError(
            "FUSSBALL.DE hat kein HTML geliefert."
        )

    print(
        "Antwort erhalten:",
        len(html),
        "Zeichen"
    )

    return html


def parse_games(html):
    """Spiele aus dem von FUSSBALL.DE gelieferten HTML lesen."""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    games = {}

    rows = soup.select(
        "tr"
    )

    print(
        "Gefundene Tabellenzeilen:",
        len(rows)
    )

    for row in rows:

        clubs = row.select(
            ".column-club .club-name"
        )

        date_cell = row.select_one(
            ".column-date"
        )

        score_link = row.select_one(
            ".column-score a[href*='/spiel/']"
        )

        if len(clubs) < 2:
            continue

        if not date_cell:
            continue

        if not score_link:
            continue

        date_text = " ".join(
            date_cell.stripped_strings
        )

        # z.B.:
        # Fr, 28.08.26 | 17:00
        match = re.search(
            r"(\d{1,2})\."
            r"(\d{1,2})\."
            r"(\d{2,4})"
            r".*?"
            r"(\d{1,2}):(\d{2})",
            date_text
        )

        if not match:
            continue

        day, month, year, hour, minute = map(
            int,
            match.groups()
        )

        if year < 100:
            year += 2000

        start = datetime(
            year,
            month,
            day,
            hour,
            minute,
            tzinfo=TZ
        )

        # Nur zukünftige Spiele.
        if start < datetime.now(TZ):
            continue

        home = " ".join(
            clubs[0].stripped_strings
        )

        away = " ".join(
            clubs[1].stripped_strings
        )

        href = score_link.get(
            "href",
            ""
        )

        match_id = ""

        match_id_match = re.search(
            r"/spiel/([^/]+)",
            href
        )

        if match_id_match:
            match_id = match_id_match.group(1)

        if not match_id:
            match_id = (
                f"{start.isoformat()}-"
                f"{home}-"
                f"{away}"
            )

        # Spielort befindet sich bei FUSSBALL.DE
        # in der folgenden row-venue-Zeile.
        location = ""

        venue_row = row.find_next_sibling(
            "tr",
            class_="row-venue"
        )

        if venue_row:

            cells = venue_row.find_all(
                "td"
            )

            if len(cells) >= 2:

                location = " ".join(
                    cells[1].stripped_strings
                )

        games[match_id] = {
            "id": match_id,
            "start": start,
            "home": home,
            "away": away,
            "location": location,
            "url": (
                "https://www.fussball.de"
                + href
                if href.startswith("/")
                else href
            ),
        }

    return sorted(
        games.values(),
        key=lambda game: game["start"]
    )


def create_calendar(games):
    """iCalendar-Datei erzeugen."""

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//tfriederichs//SG 2000 D2//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SG 2000 Mülheim-Kärlich D2",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    for game in games:

        start = game["start"]

        # Wir setzen die Kalenderdauer auf 2 Stunden.
        end = start + timedelta(
            hours=2
        )

        uid = (
            f"{TEAM_ID}-"
            f"{game['id']}"
            "@github"
        )

        summary = (
            f"{game['home']} - "
            f"{game['away']}"
        )

        description = (
            "SG 2000 Mülheim-Kärlich D2\\n"
            "Quelle: FUSSBALL.DE\\n"
            f"{game['url']}"
        )

        lines.extend(
            [
                "BEGIN:VEVENT",

                f"UID:{escape(uid)}",

                f"DTSTAMP:{timestamp}",

                (
                    "DTSTART;TZID=Europe/Berlin:"
                    f"{start:%Y%m%dT%H%M%S}"
                ),

                (
                    "DTEND;TZID=Europe/Berlin:"
                    f"{end:%Y%m%dT%H%M%S}"
                ),

                f"SUMMARY:{escape(summary)}",

                f"LOCATION:{escape(game['location'])}",

                f"DESCRIPTION:{escape(description)}",

                f"URL:{game['url']}",

                "STATUS:CONFIRMED",

                "TRANSP:OPAQUE",

                "END:VEVENT",
            ]
        )

    lines.append(
        "END:VCALENDAR"
    )

    folded_lines = []

    for line in lines:
        folded_lines.extend(
            fold_ics_line(line)
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT.write_text(
        "\r\n".join(
            folded_lines
        )
        + "\r\n",
        encoding="utf-8"
    )


def main():

    html = get_fussball_data()

    games = parse_games(
        html
    )

    print(
        "Zukünftige Spiele:",
        len(games)
    )

    # Sicherheitsfunktion:
    # Wenn FUSSBALL.DE vorübergehend keine
    # verwertbaren Spiele liefert, löschen
    # wir keinen bereits vorhandenen Kalender.
    if not games:

        if OUTPUT.exists():

            print(
                "Keine Spiele gefunden."
            )

            print(
                "Vorhandenen Kalender behalten."
            )

            return

        raise RuntimeError(
            "Keine zukünftigen Spiele gefunden."
        )

    create_calendar(
        games
    )

    print(
        f"Kalender erfolgreich erstellt: "
        f"{len(games)} Spiele"
    )

    for game in games:

        print(
            game["start"].strftime(
                "%d.%m.%Y %H:%M"
            ),
            "|",
            game["home"],
            "-",
            game["away"],
            "|",
            game["location"]
        )


if __name__ == "__main__":
    main()
