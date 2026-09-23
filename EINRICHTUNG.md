# Einrichtung Autopost (einmalig, ca. 2–3 Stunden)

Danach läuft alles von selbst:

- **Samstag:** Claude erstellt die Posts der nächsten Woche und lädt sie hoch.
- **GitHub:** rendert Grafiken und Reels, veröffentlicht pünktlich und holt sonntags die Zahlen ab.
- **Du:** musst nichts tun, außer bei Bedarf Einspruch einlegen.

Kosten: 0 €. Zugangsdaten gibst du immer selbst ein. Claude sieht und tippt keine Passwörter oder Tokens.

> Meta ändert seine Entwickler-Oberfläche öfter. Wenn ein Button anders heißt: Screenshot an Claude, wir finden ihn zusammen.

---

## Schritt 1: GitHub-Konto (10 Min)

1. Auf https://github.com/signup ein kostenloses Konto anlegen, am besten mit energyshield.kontakt@gmail.com.
2. Die GitHub-App aufs Handy laden. Damit legst du später Einspruch ein.

## Schritt 2: Repository anlegen (5 Min)

1. Auf https://github.com/new gehen.
2. Name: `energyshield-autopost`.
3. **Public** auswählen. Das ist nötig, damit Instagram die Bilder und Videos abholen kann.
   - Folge: Geplante Posts sind für jeden sichtbar, der das Repository findet. Deshalb kommen nur Post-Inhalte hinein, nie Passwörter oder interne Pläne.
4. **Kein** README, **keine** .gitignore und **keine** Lizenz anhaken.
5. Auf *Create repository* klicken.

## Schritt 3: Hochladen (5 Min)

Sag Claude: **„Verbinde autopost mit GitHub, mein Benutzername ist …"**. Claude führt die Git-Befehle aus. Beim ersten Hochladen öffnet sich ein Browserfenster, dort meldest du dich selbst bei GitHub an.

## Schritt 4: Instagram-Schnittstelle bei Meta (45–60 Min)

Voraussetzung: Der EnergyShield-Account ist ein professionelles Konto (Creator reicht).

1. https://developers.facebook.com öffnen, mit deinem Facebook-Konto anmelden und dich als Entwickler registrieren. Das ist kostenlos.
2. **App erstellen** anklicken.
   - Anwendungsfall: **„Nachrichten und Inhalte auf Instagram verwalten"** (engl. *Manage messaging & content on Instagram*)
   - App-Name: `EnergyShield Autopost`
   - Unternehmensportfolio: keins
3. Im App-Dashboard den Anwendungsfall öffnen und dort **„API-Einrichtung mit Instagram-Login"** auswählen.
4. Unter **Berechtigungen** diese drei hinzufügen, falls sie nicht schon da sind:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
   - `instagram_business_manage_insights`
5. Unter **App-Rollen → Rollen** den EnergyShield-Instagram-Account als **Instagram-Tester** hinzufügen.
   - Dann in der Instagram-App: *Einstellungen → Website-Berechtigungen → Apps und Websites → Tester-Einladungen* → annehmen.
   - Falls es den Punkt nicht gibt: im Browser auf instagram.com unter *Einstellungen → Apps und Websites* nachsehen.
6. Zurück bei **„API-Einrichtung mit Instagram-Login"**: Unter **„Zugriffstokens generieren"** auf *Konto hinzufügen* klicken, mit dem EnergyShield-Instagram anmelden und zustimmen.
7. Jetzt siehst du zwei Dinge:
   - die **Instagram-Konto-ID**, eine lange Zahl
   - einen **Token** (Button *Token generieren*). Der Token wird nur einmal angezeigt, also sofort kopieren.
   - Die App kann im Entwicklungsmodus bleiben. Für den eigenen Account reicht das, eine App-Prüfung durch Meta ist nicht nötig.

## Schritt 5: Token und ID bei GitHub hinterlegen (5 Min)

1. Im Repository auf **Settings → Secrets and variables → Actions → New repository secret** klicken.
2. Zwei Secrets anlegen:
   - Name `IG_TOKEN`, Wert: der Token aus Schritt 4
   - Name `IG_USER_ID`, Wert: die Konto-ID aus Schritt 4

## Schritt 6: Automatische Token-Verlängerung (10 Min)

Der Instagram-Token läuft nach 60 Tagen ab, das Event ist aber erst in gut 4 Monaten. Damit GitHub den Token selbst erneuern kann:

1. https://github.com/settings/personal-access-tokens/new öffnen.
2. Token name: `autopost-token-verlaengern`, Expiration: **31.03.2027**.
3. Repository access: **Only select repositories** → `energyshield-autopost`.
4. Permissions → Repository permissions → **Secrets: Read and write**.
5. Auf *Generate token* klicken, den Token kopieren und als drittes Secret mit Namen `GH_PAT` speichern (wie in Schritt 5).

## Schritt 7: Testlauf (10 Min)

1. Im Repository den Tab **Actions** öffnen und die Workflows aktivieren, falls GitHub fragt.
2. Workflow **Rendern** → *Run workflow*. Nach ca. 3 Minuten `VORSCHAU.md` öffnen: Es sollten 4 Testgrafiken zu sehen sein (Karussell mit 3 Grafiken plus Countdown-Story). Diese Testposts werden nie veröffentlicht.
3. Workflow **Posten** → *Run workflow* mit Haken bei *Nur testen*. Er sollte grün durchlaufen.
4. Workflow **Zahlen** → *Run workflow*. Danach steht in `stats/zahlen.csv` die aktuelle Follower-Zahl. Damit ist bewiesen, dass die Verbindung zu Instagram funktioniert.
5. Workflow **Token verlängern** → *Run workflow*. Er sollte grün durchlaufen.
6. Claude Bescheid geben. Die Testposts werden dann gelöscht und der erste echte Wochen-Batch läuft.

---

## Im Alltag

| Was | Wie |
|---|---|
| **Vorschau ansehen** | Datei `VORSCHAU.md` im Repository öffnen (auch in der GitHub-App) |
| **Einspruch** | Beim Post auf `post.json` tippen → Stift-Symbol → `"geplant"` in `"stop"` ändern → *Commit changes*. Oder den Ordner löschen |
| **Einspruchsfrist** | Jeder Post geht frühestens 24 h nach dem Hochladen online. Der Samstags-Batch plant nie vor Dienstag, du hast also mindestens 2 Tage |
| **Fehler** | GitHub schickt bei einem fehlgeschlagenen Workflow eine E-Mail. Die Fehlermeldung steht auch in `VORSCHAU.md` beim Post |
| **Pünktlichkeit** | GitHub startet geplante Läufe manchmal 5–20 Minuten später. Aus 18:30 Uhr kann also 18:45 Uhr werden |
| **Nicht automatisch** | Story-Sticker (Countdown, Umfrage, Link) und Musik aus der Instagram-Bibliothek. Die stehen als Aufgabe für Volkan im Wochenplan |
