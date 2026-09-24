# Einrichtung Autopost mit Buffer (einmalig, ca. 15 Minuten)

- ✅ Schritt 1–3 (GitHub-Konto, Repository, Hochladen) sind erledigt (24.9.2026).
- ❌ Die Meta-Entwickler-App wird **nicht** gebraucht.

Danach läuft alles von selbst:
- **Samstag:** Claude erstellt die Posts der nächsten Woche.
- **GitHub:** baut Grafiken und Reels und übergibt sie 4 Tage vorher an Buffer.
- **Buffer:** postet pünktlich.

Kosten: 0 €. Zugangsdaten gibst du immer selbst ein.

---

## Schritt 4: Buffer-Konto (3 Min)

1. Auf https://buffer.com auf *Get started* klicken und ein kostenloses Konto anlegen, am besten mit energyshield.kontakt@gmail.com.
2. Den **Free**-Tarif wählen. Keine Testphase starten, keine Zahlungsdaten eingeben.
3. Die Buffer-App aufs Handy laden. Dort siehst du die Warteschlange mit Vorschau und legst Einspruch ein.

## Schritt 5: Instagram verbinden (3 Min)

1. In Buffer auf *Channels → Connect a channel → Instagram* klicken.
2. Mit dem EnergyShield-Instagram anmelden und Buffer den Zugriff erlauben.
   - Wählen, dass Buffer **automatisch posten** darf (nicht nur erinnern).
   - Eine Facebook-Seite ist nicht nötig.

## Schritt 6: API-Schlüssel bei GitHub hinterlegen (5 Min)

1. In Buffer https://publish.buffer.com/settings/api öffnen → **Neuen API-Schlüssel erstellen**. Den Schlüssel kopieren, er wird nur einmal angezeigt.
2. Auf GitHub im Repository auf **Settings → Secrets and variables → Actions → New repository secret** gehen.
   - Name: `BUFFER_API_KEY`
   - Wert: der Schlüssel
3. Speichern.

## Schritt 7: Verbindungstest (2 Min)

1. Im Repository **Actions → An Buffer senden → Run workflow** öffnen, den Haken bei *Nur testen* lassen und starten.
2. Wenn der Lauf grün ist und im Log „Instagram-Kanal in Buffer: …" steht, steht die Verbindung.
3. Claude Bescheid geben.

---

## Im Alltag

| Was | Wie |
|---|---|
| **Vorschau** | Bis 4 Tage vor dem Termin: `VORSCHAU.md` im Repository. Danach: Warteschlange in der Buffer-App |
| **Einspruch** | Am einfachsten in der **Buffer-App den Post löschen oder bearbeiten**. Früher: in `VORSCHAU.md` → `post.json` → `"geplant"` in `"stop"` ändern |
| **Collab-Posts** | Buffer postet ohne Collab. Danach in Instagram beim Post auf „…" → *Mitwirkende einladen* und den DJ einladen. Das steht jeweils als Aufgabe für Volkan im Wochenplan |
| **Nicht automatisch** | Story-Sticker (Countdown, Umfrage, Link) und Musik aus der Instagram-Bibliothek. Das steht als Aufgabe für Volkan im Wochenplan |
| **Zahlen** | Phil trägt sonntags die Instagram-Zahlen von Hand ein (Instagram-App → Insights) |
| **Fehler** | GitHub schickt bei einem fehlgeschlagenen Lauf eine E-Mail. Die Fehlermeldung steht auch in `VORSCHAU.md` beim Post |
| **Grenze Gratis-Tarif** | Buffer hält höchstens 10 geplante Posts gleichzeitig. Das System hält sich automatisch daran |
