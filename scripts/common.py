"""Gemeinsame Helfer für Rendern, Posten und Statistik."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
POSTED = ROOT / "posted"
TEMPLATES = ROOT / "templates"
BRAND = ROOT / "brand"

TYPEN = {"bild", "karussell", "reel", "story"}


def jetzt():
    return datetime.now(timezone.utc)


def zeit(text):
    """ISO-Zeit mit Zeitzone, z. B. 2026-10-06T18:30:00+02:00."""
    t = datetime.fromisoformat(text)
    if t.tzinfo is None:
        raise ValueError(f"Zeit ohne Zeitzone: {text}")
    return t


def lade_posts(ordner=QUEUE):
    """Alle Posts als Liste von (ordner, daten), sortiert nach Veröffentlichungszeit."""
    posts = []
    if not ordner.exists():
        return posts
    for datei in sorted(ordner.glob("*/post.json")):
        daten = json.loads(datei.read_text(encoding="utf-8"))
        posts.append((datei.parent, daten))
    posts.sort(key=lambda p: p[1].get("publish_at", ""))
    return posts


def speichere(ordner, daten):
    (ordner / "post.json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def medien_hash(ordner, daten):
    """Ändert sich, sobald Texte, Vorlagen oder Rohdateien des Posts sich ändern."""
    h = hashlib.sha256()
    relevant = {k: v for k, v in daten.items() if k not in ("status", "versuche", "letzter_fehler")}
    h.update(json.dumps(relevant, sort_keys=True, ensure_ascii=False).encode())
    for datei in sorted(TEMPLATES.glob("*")):
        h.update(datei.read_bytes())
    for datei in sorted(ordner.iterdir()):
        if datei.is_file() and datei.name != "post.json":
            h.update(datei.name.encode())
            h.update(str(datei.stat().st_size).encode())
    return h.hexdigest()[:16]


def ist_aktuell(ordner, daten):
    """True, wenn die gerenderten Medien zum aktuellen Stand des Posts passen."""
    h = ordner / "media" / ".hash"
    return h.exists() and h.read_text().strip() == medien_hash(ordner, daten)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def cdn_url(ordner, datei):
    """Öffentliche, unveränderliche URL (fester Commit).

    Bilder direkt von GitHub (liefert image/jpeg sofort), Videos über jsDelivr,
    weil GitHub Videos als application/octet-stream ausliefert.
    """
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = git("rev-parse", "HEAD")
    pfad = (ordner / "media" / datei).relative_to(ROOT).as_posix()
    if datei.endswith(".mp4"):
        return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{pfad}"
    return f"https://raw.githubusercontent.com/{repo}/{sha}/{pfad}"
