# SG 2000 Mülheim-Kärlich D2 – iPhone-Kalender

Der Workflow liest den Spielplan der D2 direkt von FUSSBALL.DE und erzeugt täglich `spielplan.ics`.

## Einrichtung
1. Dateien ins GitHub-Repository hochladen.
2. Unter **Settings → Pages** als Quelle **GitHub Actions** auswählen.
3. Unter **Actions** den Workflow einmal mit **Run workflow** starten.
4. Danach lautet die Kalenderadresse:
   `https://DEIN-BENUTZERNAME.github.io/DEIN-REPOSITORY/spielplan.ics`

## iPhone
**Einstellungen → Apps → Kalender → Kalenderaccounts → Account hinzufügen → Andere → Kalenderabo hinzufügen**
und dort die `spielplan.ics`-Adresse eintragen.

Es werden nur zukünftige Spiele übernommen. Datum, Uhrzeit und Spielort werden bei der täglichen Aktualisierung neu aus FUSSBALL.DE gelesen.
