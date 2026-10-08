# Post-Format (für den Content-Agenten)

Jeder Post ist ein Ordner in `queue/` mit einer `post.json` und den benötigten Rohdateien (Fotos, Clips, Audio).

**Ordnername:** `JJJJ-MM-TT_HHMM_kurzname`, z. B. `2026-10-06_1830_wer-ist-energyshield`

## post.json

```json
{
  "publish_at": "2026-10-06T18:30:00+02:00",
  "erstellt_am": "2026-10-03T10:00:00+02:00",
  "typ": "reel",
  "status": "geplant",
  "caption": "Erste Zeile ist der Hook.\n\nText …\n\n#drumandbass #dnb",
  "collaborators": ["dj_handle"],
  "slides": [],
  "reel": {}
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `publish_at` | ja | Veröffentlichungszeit **mit Zeitzone** (Sommerzeit `+02:00` bis 24.10.2026, danach Winterzeit `+01:00`) |
| `erstellt_am` | ja | Jetzt. Der Post geht frühestens 24 h danach online (Einspruchsfrist) |
| `typ` | ja | `bild`, `karussell`, `reel` oder `story` |
| `status` | ja | `geplant` (wird gepostet), `stop` (Einspruch), `test` (wird nur gerendert), `freigabe` (Reserve: wird gerendert, geht nicht an Buffer, bis Claude auf `geplant` umstellt) |
| `caption` | nein | Text unter dem Post. Nicht bei Stories (die haben keine Caption) |
| `collaborators` | nein | Instagram-Namen ohne @. **Buffer kann keine Collab-Posts.** Der Post geht normal raus, danach lädt Volkan die Personen in Instagram als Mitwirkende ein. Deshalb jeden Collab-Post auch unter „Manuell für Volkan" notieren |
| `slides` | bei bild/karussell/story | Liste von Grafiken (siehe unten). Karussell: 2–10 |
| `reel` | bei reel, optional bei story | Video-Angaben (siehe unten) |

## Slide (Grafik)

```json
{ "vorlage": "feed", "kicker": "SAVE THE DATE", "titel": "30.01.\nBASTION", "text": "Unser Club-Debut.", "fuss": "EVENT", "bild": "foto.jpg", "akzent": "blau" }
```

| Feld | Bedeutung |
|---|---|
| `vorlage` | `feed` (1080×1350), `lineup` (1080×1350, Name unten über Foto), `story` (1080×1920), `countdown` (1080×1920, riesige Zahl im `titel`), `quadrat` (1080×1080, wie feed, für Shield-Sessions-Karussells), `cover` (1080×1080, Shield-Sessions-Cover, siehe unten) |
| `kicker` | kleine Zeile über der Headline, Akzentfarbe |
| `titel` | Headline, wird automatisch GROSS geschrieben. `\n` = Zeilenumbruch. Max. ca. 12 Zeichen pro Zeile bei feed |
| `text` | Fließtext, 1–2 kurze Sätze |
| `fuss` | Kleingedrucktes unten. `"EVENT"` setzt automatisch: *Sa 30.01.2027 · Club Bastion Kirchheim · Nur Abendkasse · Ab 18 · Nur 120 Plätze* |
| `bild` | optional: Foto im Post-Ordner als Hintergrund. Mit Foto sitzt der Text unten über dem Fuß, das Motiv bleibt oben frei. Kurze Titel (1–2 Wörter pro Zeile) wirken am besten. Fotos kommen aus `Rohmaterial/fotos/` und werden in den Post-Ordner kopiert. |
| `akzent` | `blau` (Cyan, Standard, Deep), `liquid` (Mint), `neuro` (Violett, Neurofunk), `jumpup` (Orange), `halftime` (Pink) |

Leere Felder werden einfach weggelassen. Frame und Logo kommen automatisch.

## Shield Sessions (Mix-Serie, Karussell mit Hörproben)

```json
{
  "typ": "karussell",
  "mix_drive_id": "1xlrxP-yhGsg6F3V541URPrgLc_R2HPnQ",
  "slides": [
    { "vorlage": "cover", "dj": "Kruxer", "vol": 1, "stil": "Deep", "bpm": 174 },
    { "vorlage": "quadrat", "bild": "dj.jpg", "akzent": "blau", "kicker": "Resident · Vol. 01", "titel": "Kruxer", "fuss": "Shield Sessions · Jeden Sonntag" }
  ],
  "hoerproben": [
    { "im_mix": "12:30", "dauer": 30 },
    { "im_mix": "31:05", "dauer": 30 },
    { "im_mix": "54:40", "dauer": 30 }
  ]
}
```

- `cover`: `dj`, `vol` (Zahl), `stil` (ein oder mehrere, mit Komma). Farbe kommt automatisch vom ersten Stil (Deep = Cyan, Halftime = Pink, Neurofunk = Violett, Jump-Up = Orange, Liquid = Mint). Kruxer, Stone D, Jhinx und Ranj haben je ein eigenes Schild, alle anderen das Standard-Schild. Zusätzlich entsteht `media/soundcloud.jpg` in 2160 px für SoundCloud (wird nicht gepostet).
- `hoerproben`: **Normalfall:** `{ "im_mix": "3:05", "dauer": 30 }` plus auf Post-Ebene `"mix_drive_id": "<Drive-ID des Mixes>"` – GitHub lädt den Mix aus der (per Link freigegebenen) Drive und schneidet ab `im_mix`. Alternativ `audio` (Datei im Post-Ordner, optional `start` in Sekunden); `im_mix` ist dann nur die Anzeige. `dauer` 30, höchstens 59. Design: Hot-Cue-Pad A/B/C, CDJ-Wellenform, BPM aus `"bpm"` im Cover-Slide, Stil-Tag. Werden zu Video-Slides nach den Bild-Slides (3.mp4, 4.mp4, 5.mp4). `"__testbild__"`-artig gibt es `"__testton__"` nur für Tests.
- Alle Slides eines Shield-Sessions-Karussells sind quadratisch: nur `cover` und `quadrat` verwenden.

## Shield Radar (Szene-News, alle 2 Wochen Do 18:30)

Spec und Regeln: `Automatisierung/shield-radar.md` (nur Fakten mit Quelle, keine fremden Bilder, keine Emojis auf den Slides). Karussell 1080×1350 aus `radar-*`-Vorlagen; das Radar auf dem Cover, Seitenzahlen und das Mini-Radar entstehen automatisch aus den Meldungen.

```json
{
  "typ": "karussell",
  "slides": [
    { "vorlage": "radar-cover", "ausgabe": 2, "datum": "29.10.2026" },
    { "vorlage": "radar-meldung", "ring": "welt", "kategorie": "Release", "ort": "London",
      "titel": "Schlagzeile", "anriss": "Kurzfassung für Cover und Story", "text": "2–3 Sätze.",
      "wichtig": "Ein Satz Einordnung.", "quelle": "Quelle, Datum" },
    { "vorlage": "radar-kurz", "punkte": [ { "ring": "lokal", "text": "Ein Satz.", "quelle": "Quelle" } ] },
    { "vorlage": "radar-wissen", "begriff": "Jungle", "titel": "Was ist Jungle?", "text": "2–4 Sätze.", "quelle": "Quelle" },
    { "vorlage": "radar-ende", "frage": "Frage an die Community?", "naechste": "12.11." }
  ]
}
```

| Vorlage | Pflicht | Optional |
|---|---|---|
| `radar-cover` (immer Slide 1) | `ausgabe` (Zahl), `datum` | – |
| `radar-meldung` (2–4 Stück, wichtigste zuerst) | `ring` (`lokal`, `de`, `welt`), `titel`, `text`, `quelle` | `kategorie`, `ort`, `anriss`, `wichtig` |
| `radar-kurz` | `punkte` (2–3, je `ring`, `text`, `quelle`) | – |
| `radar-wissen` | `begriff` (ein Wort, wird riesig gesetzt), `text` | `titel`, `quelle` |
| `radar-ende` (immer letzte Slide) | `frage` | `naechste` (Datum der nächsten Ausgabe) |
| `radar-story` (eigener Post, `typ: story`) | `ausgabe`, `datum`, `meldungen` (je `ring`, `titel`) | – |

- Zu langer Text wird erst verkleinert (Fließtext nie unter 32 px); passt er dann immer noch nicht, bricht das Rendern mit „Zu viel Text für die Slide“ ab (steht als `letzter_fehler` in der post.json). Fehlt eine `quelle`, ebenfalls.
- Vor dem Push lokal testen: `post.json` nach `tests/radar/faelle/ausgabeNN.json` kopieren, dann `powershell -File tests\radar\radar-test.ps1 -Fall ausgabeNN -Bild` (Bilder in `tests/radar/out/`).

## Behind the Shield (Resident-Vorstellungen, im Chat gebaut)

Spec und Ablauf: `../Automatisierung/behind-the-shield.md` (Inhalte nur aus dem Fragebogen, nichts erfinden, keine Emojis auf den Slides). Karussell 1080 × 1350 aus `bts-*`-Vorlagen. Akzentfarbe, Schild, Name und Handle kommen aus `resident` im Cover; Kopfleiste, Fortschritt und Fuß entstehen automatisch.
**Vor dem OK des Residents nichts in dieses (öffentliche) Repo:** Der Entwurf entsteht in `../Content/Behind-the-Shield/<Resident>/` (post.json, Fotos, Antworten) und wird dort getestet. Erst nach dem OK kommt er nach `queue/`, mit Status `geplant`, und wird gepusht. Kopiert werden nur `post.json`, die Fotos und das fertige Video (`video`), nicht `antworten.md`, das Visualizer-Original und der Ordner `fertig/`. Collab-Einladung in `Content/KW<NN>-<JJJJ>.md` unter „Manuell für Volkan“ eintragen. Der Status `freigabe` (wird gerendert, geht nicht an Buffer) bleibt nur als Reserve.

```json
{
  "typ": "karussell",
  "status": "geplant",
  "collaborators": ["stone_d_97"],
  "slides": [
    { "vorlage": "bts-cover", "resident": "Stone D", "folge": 2, "bild": "portraet.jpg", "fokus": "55% 25%",
      "stile": ["Halftime", "Deep"], "seit": "2018" },
    { "vorlage": "bts-steckbrief", "vorname": "Max", "rolle": "Resident und Technik", "name_herkunft": "1–2 Sätze." },
    { "vorlage": "bts-sound", "worte": ["Tief", "Dunkel", "Treibend"], "fuer_neue": "1 Satz.", "erklaert": "1–2 Sätze zum Hauptstil." },
    { "vorlage": "bts-anfang", "zitat": "2–3 Sätze.", "moment": "1–2 Sätze." },
    { "vorlage": "bts-tracks", "tracks": ["Artist – Title", "Artist – Title", "Artist – Title"] },
    { "vorlage": "bts-abseits", "bild": "pult.jpg", "funfact": "1 Satz.", "abseits": "1 Satz." },
    { "vorlage": "bts-bastion", "set": "1–2 Sätze.", "an_neue": "1 Satz." }
  ]
}
```

| Vorlage | Pflicht | Optional |
|---|---|---|
| `bts-cover` (immer Slide 1) | `resident` (KruXer, Stone D, Jhinx, Ranj), `folge` (Zahl), `bild`, `stile` (Liste, der erste ist der Hauptstil), `seit` | `fokus` (Lage des Gesichts, `"x% y%"`, Standard `"50% 30%"`) |
| `bts-steckbrief` | `rolle` | `vorname` (nur mit Zustimmung), `name_herkunft` |
| `bts-sound` | `worte` (genau 3), `fuer_neue`, `erklaert` | – |
| `bts-anfang` | `zitat`, `moment` | – |
| `bts-tracks` | `tracks` (genau 3, „Künstler – Titel“; ohne Trennstrich nur Titel) | – |
| `bts-produktion` (optional, nach `bts-tracks`, Video-Slide) | `titel` (Tracktitel), `video` (fertiges MP4, z. B. `produktion.mp4`) | `kuenstler` (Standard: Name des Residents), `visualizer` (Original-Video aus TouchDesigner, nur im Entwurf) |
| `bts-abseits` (ganze Slide optional) | `funfact` oder `abseits` | `bild` (Pult-Foto), `fokus` (Standard `"50% 50%"`) |
| `bts-bastion` (immer letzte Slide) | `set` | `an_neue` |

- Das Cover-Foto wird in der Resident-Farbe eingefärbt, die Fotos auf Steckbrief und Abseits bleiben natürlich. Sitzt das Gesicht schlecht im Schild: `fokus` anpassen.
- `bts-produktion` (seit 8.10.2026 komplett): Video-Slide für einen eigenen Track. Die Grafik hat Text links und rechts einen 9:16-Rahmen (461 × 820). Das Visualizer-Video aus TouchDesigner (9:16, z. B. 1080 × 1920 oder 720 × 1280, 3–60 s, mit Ton) liegt als `visualizer` im Entwurfsordner. **`tests/bts/bts-fertig.ps1` setzt es lokal in den Rahmen** (Windows-Bordmittel, kein ffmpeg) und speichert das fertige MP4 (1080 × 1350, H.264/AAC, max. 18 MB) unter dem Namen aus `video`. GitHub rendert diese Slide nicht, sondern prüft das MP4 (Größe, 1080 × 1350, Ton, Länge) und übernimmt es als `<n>.mp4` an seiner Stelle im Karussell.
- Tracktitel werden nie mitten im Wort getrennt. Zu lange Wörter werden verkleinert; reicht das nicht, kommt „Ein Wort ist zu lang für die Slide“. Schöner bei langen Titeln: weiches Trennzeichen an der gewünschten Stelle, in der post.json `"Extra­terrestrial"` (erscheint nur beim Umbruch als Strich).
- **Ordnername:** `queue/<JJJJ-MM-TT>_<HHMM>_behind-the-shield-<resident>/` (z. B. `2026-10-20_1830_behind-the-shield-stoned`). Die Samstags-Aufgabe erkennt die Folgen an diesem Namen.
- Testen direkt aus dem Entwurfsordner (kopiert nur nach `tests/bts/out/`, nichts Versioniertes): `powershell -NoProfile -ExecutionPolicy Bypass -File tests\bts\bts-test.ps1 -Post ..\Content\Behind-the-Shield\<Resident> -Bild`. Die Bilder in `tests/bts/out/` ansehen und Oliver als Vorschau zeigen.
- **Fertiger Beitrag:** `powershell -NoProfile -ExecutionPolicy Bypass -File tests\bts\bts-fertig.ps1 -Post ..\Content\Behind-the-Shield\<Resident>` prüft alle Slides, baut die Video-Slide und legt den Beitrag so ab, wie er gepostet wird: `<Entwurfsordner>\fertig\` mit `1.jpg`, `2.jpg` …, der Video-Slide als `<n>.mp4` und `caption.txt`. Das schickt Oliver dem Resident zur Freigabe.
- Fehlermeldungen und Abhilfe:
  - „Zu viel Text für die Slide“, „Text läuft seitlich über den Rand“: Antwort kürzen, Sinn und Wortlaut des Residents möglichst behalten.
  - „Ein Wort ist zu lang für die Slide“: auf Slide 3 ein kürzeres Wort wählen (mit dem Resident absprechen).
  - „Track-Titel zu lang“: Zusätze wie Remix- oder Feature-Angaben weglassen. „Stile zu lang für das Cover“: höchstens 2–3 Stile.
  - „Foto „…“ nicht ladbar“ bzw. „Bild '…' fehlt im Post-Ordner“: Dateiname prüfen, Foto in den Post-Ordner kopieren.
  - „Unbekannter Resident“, „Feld … fehlt“, „braucht genau 3 …“, „Erste Slide muss bts-cover sein“: Format nach dieser Tabelle korrigieren.

## Reel (Video)

```json
{
  "clip": "clip.mp4", "start": 12, "dauer": 15,
  "audio": "track.mp3", "audio_start": 64,
  "overlay": { "kicker": "LIQUID", "titel": "VIER LEUTE.\nEIN SOUND.", "akzent": "liquid" },
  "hook_sekunden": 3,
  "titelbild_sekunde": 1.5
}
```

| Feld | Bedeutung |
|---|---|
| `clip` | Videodatei im Post-Ordner. Wird automatisch auf 9:16 zugeschnitten. `"__testbild__"` erzeugt einen Testclip (nur für Tests) |
| `start`, `dauer` | Ausschnitt in Sekunden. Dauer 5–90 s, empfohlen 7–30 s |
| `audio`, `audio_start` | optional: eigener Track eines DJs (**nur mit Freigabe**). Ohne Angabe bleibt der Originalton |
| `overlay` | optional: Texteinblendung (Hook) wie ein Slide, ohne Hintergrund |
| `hook_sekunden` | optional: Overlay nur die ersten X Sekunden zeigen |
| `titelbild_sekunde` | optional: welcher Moment des Videos als Titelbild dient (eigene Titelbilder erlaubt Buffer nicht). Tipp: eine Sekunde wählen, in der das Hook-Overlay zu sehen ist |

## Grenzen

- Story-Sticker (Countdown, Umfrage, Link) gehen **nicht** über die API. Solche Stories als Aufgabe für Volkan notieren.
- Musik aus der Instagram-Bibliothek geht nicht. Ton muss im Clip oder als eigene Audiodatei vorliegen.
- Dateien im Post-Ordner klein halten: Clips max. 50 MB, fertiges Reel max. 19 MB (wird automatisch komprimiert).
- Veröffentlicht wird über **Buffer (Gratis-Tarif)**: höchstens 10 geplante Posts gleichzeitig. Das System übergibt deshalb erst 4 Tage vorher. Mehr als ca. 2 Posts plus Stories pro Tag nicht einplanen.
- Posts mindestens 2 Tage im Voraus anlegen: Übergabe frühestens 24 h nach `erstellt_am`, sonst Status `verpasst`.
