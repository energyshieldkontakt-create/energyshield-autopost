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
| `collaborators` | nein | Bis zu 3 Instagram-Namen ohne @. Nicht bei Stories. Die Person bekommt eine Collab-Einladung |
| `slides` | bei bild/karussell/story | Liste von Grafiken (siehe unten). Karussell: 2–10 |
| `reel` | bei reel, optional bei story | Video-Angaben (siehe unten) |

## Slide (Grafik)

```json
{ "vorlage": "feed", "kicker": "SAVE THE DATE", "titel": "30.01.\nBASTION", "text": "Unser Club-Debut.", "fuss": "EVENT", "bild": "foto.jpg", "akzent": "blau" }
```

| Feld | Bedeutung |
|---|---|
| `vorlage` | `feed` (1080×1350), `lineup` (1080×1350, Name unten über Foto), `story` (1080×1920), `countdown` (1080×1920, riesige Zahl im `titel`) |
| `kicker` | kleine Zeile über der Headline, Akzentfarbe |
| `titel` | Headline, wird automatisch GROSS geschrieben. `\n` = Zeilenumbruch. Max. ca. 12 Zeichen pro Zeile bei feed |
| `text` | Fließtext, 1–2 kurze Sätze |
| `fuss` | Kleingedrucktes unten. `"EVENT"` setzt automatisch: *Sa 30.01.2027 · Club Bastion Kirchheim · Nur Abendkasse · Ab 18 · Nur 120 Plätze* |
| `bild` | optional: Foto im Post-Ordner als Hintergrund (wird abgedunkelt) |
| `akzent` | `blau` (Standard), `liquid` (Türkis) oder `neuro` (Violett) |

Leere Felder werden einfach weggelassen. Frame und Logo kommen automatisch.

## Reel (Video)

```json
{
  "clip": "clip.mp4", "start": 12, "dauer": 15,
  "audio": "track.mp3", "audio_start": 64,
  "overlay": { "kicker": "LIQUID", "titel": "VIER LEUTE.\nEIN SOUND.", "akzent": "liquid" },
  "hook_sekunden": 3,
  "cover": { "kicker": "ENERGYSHIELD", "titel": "WER SIND WIR?" }
}
```

| Feld | Bedeutung |
|---|---|
| `clip` | Videodatei im Post-Ordner. Wird automatisch auf 9:16 zugeschnitten |
| `start`, `dauer` | Ausschnitt in Sekunden. Dauer 5–90 s, empfohlen 7–30 s |
| `audio`, `audio_start` | optional: eigener Track eines DJs (**nur mit Freigabe**). Ohne Angabe bleibt der Originalton |
| `overlay` | optional: Texteinblendung (Hook) wie ein Slide, ohne Hintergrund |
| `hook_sekunden` | optional: Overlay nur die ersten X Sekunden zeigen |
| `cover` | optional: Titelbild des Reels (Story-Vorlage) |

## Grenzen

- Story-Sticker (Countdown, Umfrage, Link) gehen **nicht** über die API. Solche Stories als Aufgabe für Volkan notieren.
- Musik aus der Instagram-Bibliothek geht nicht. Ton muss im Clip oder als eigene Audiodatei vorliegen.
- Dateien im Post-Ordner klein halten: Clips max. 50 MB, fertiges Reel max. 19 MB (wird automatisch komprimiert).
- Max. 3 Collab-Partner pro Post.
