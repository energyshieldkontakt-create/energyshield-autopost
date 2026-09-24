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
| `status` | ja | `geplant` (wird gepostet), `stop` (Einspruch), `test` (wird nur gerendert) |
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
  "slides": [
    { "vorlage": "cover", "dj": "Kruxer", "vol": 1, "stil": "Deep" },
    { "vorlage": "quadrat", "bild": "dj.jpg", "akzent": "blau", "kicker": "Resident · Vol. 01", "titel": "Kruxer", "text": "2–3 Sätze.", "fuss": "Shield Sessions · Jeden Sonntag" }
  ],
  "hoerproben": [
    { "audio": "hoerprobe-1.mp3", "im_mix": "12:30", "dauer": 30 },
    { "audio": "hoerprobe-2.mp3", "im_mix": "31:05", "dauer": 30 },
    { "audio": "hoerprobe-3.mp3", "im_mix": "54:40", "dauer": 30 }
  ]
}
```

- `cover`: `dj`, `vol` (Zahl), `stil` (ein oder mehrere, mit Komma). Farbe kommt automatisch vom ersten Stil (Deep = Cyan, Halftime = Pink, Neurofunk = Violett, Jump-Up = Orange, Liquid = Mint). Kruxer, Stone D, Jhinx und Ranj haben je ein eigenes Schild, alle anderen das Standard-Schild. Zusätzlich entsteht `media/soundcloud.jpg` in 2160 px für SoundCloud (wird nicht gepostet).
- `hoerproben`: MP3 im Post-Ordner, `start` (optional, Sekunden in der Datei), `dauer` (max. 30 empfohlen, höchstens 59), `im_mix` (nur Anzeige: Stelle im ganzen Mix). Werden zu Video-Slides nach den Bild-Slides (3.mp4, 4.mp4, 5.mp4). `"__testbild__"`-artig gibt es `"__testton__"` nur für Tests.
- Alle Slides eines Shield-Sessions-Karussells sind quadratisch: nur `cover` und `quadrat` verwenden.

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
