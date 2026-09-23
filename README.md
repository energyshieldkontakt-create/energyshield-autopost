# EnergyShield Autopost

Automatisches Posten auf Instagram für EnergyShield.

```
Claude (Samstag)  →  queue/<post>/post.json + Rohmaterial  →  GitHub
GitHub „Rendern"  →  Grafiken (HTML → JPEG) + Reels (ffmpeg)  →  VORSCHAU.md
GitHub „Posten"   →  alle 15 Min: fällige Posts über die Instagram-API veröffentlichen  →  posted/
GitHub „Zahlen"   →  sonntags Follower & Reichweite  →  stats/zahlen.csv
```

- Einrichtung: [EINRICHTUNG.md](EINRICHTUNG.md)
- Format der Posts: [POST-FORMAT.md](POST-FORMAT.md)
- Aktuelle Warteschlange: [VORSCHAU.md](VORSCHAU.md)
