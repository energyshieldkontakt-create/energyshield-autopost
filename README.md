# EnergyShield Autopost

Automatisches Posten auf Instagram für EnergyShield, über Buffer (Gratis-Tarif).

> **Seit 3.11.2026 abgeschaltet (Oliver):** Nichts geht mehr automatisch an Buffer, der Workflow „An Buffer senden“ läuft nur noch von Hand. Das Repo rendert weiter Grafiken und Hörproben (Shield Sessions), Oliver lädt alles selbst hoch. Neue Posts haben den Status `freigabe`, die gestoppten Posts von KW45 den Status `stop`.

```
Claude (Samstag)       →  queue/<post>/post.json + Rohmaterial  →  GitHub
GitHub „Rendern"       →  Grafiken (HTML → JPEG) + Reels (ffmpeg)  →  VORSCHAU.md
GitHub „An Buffer"     →  stündlich: Posts der nächsten 4 Tage an Buffer übergeben  →  posted/
Buffer                 →  veröffentlicht pünktlich auf Instagram
```

- Einrichtung: [EINRICHTUNG.md](EINRICHTUNG.md)
- Format der Posts: [POST-FORMAT.md](POST-FORMAT.md)
- Aktuelle Warteschlange: [VORSCHAU.md](VORSCHAU.md)
