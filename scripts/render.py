#!/usr/bin/env python3
"""Rendert Grafiken (HTML -> JPEG) und Reels (ffmpeg) für alle Posts in queue/.

Läuft in GitHub Actions. Rendert nur Posts, deren Inhalt sich seit dem letzten
Rendern geändert hat, und schreibt danach VORSCHAU.md neu.
"""
import html
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image
from playwright.sync_api import sync_playwright

from common import BRAND, ROOT, TEMPLATES, TYPEN, ist_aktuell, lade_posts, medien_hash, speichere, zeit

# Vorlage -> (Breite, Höhe, CSS-Klassen)
FORMATE = {
    "feed": (1080, 1350, "feed"),
    "lineup": (1080, 1350, "lineup"),
    "story": (1080, 1920, "story"),
    "countdown": (1080, 1920, "countdown"),
    "overlay": (1080, 1920, "overlay transparent"),
}
# Farben aus den bisherigen Flyern: Cyan-Neon (Standard), Mint (Talent Night), Violett
AKZENTE = {"blau": "#2EE6F5", "liquid": "#6FF5C2", "neuro": "#9D7BFF"}
# Fußbereich im Flyer-Stil: Info-Leiste, großes Datum, zwei Eck-Infos
FUSS_EVENT = (
    '<div class="pill"><span class="pill-l">Drum and Bass</span><span class="pill-r">Nur 120 Plätze</span></div>'
    '<div class="datum">SA 30.01.27</div>'
    '<div class="infozeile"><span>Club Bastion · Kirchheim</span><span>Abendkasse · Ab 18</span></div>'
)
# Verkleinert die Headline, bis sie in die Breite passt und weder Kopf noch Fuß berührt
FIT_JS = """
document.fonts.ready.then(() => {
  const h1 = document.querySelector('h1[data-fit]');
  const main = document.querySelector('main');
  const kopf = document.querySelector('.marke');
  const fuss = document.querySelector('footer');
  if (!h1 || !h1.textContent.trim()) return true;
  const zuGross = () => {
    if (h1.scrollWidth > h1.clientWidth + 1) return true;
    const m = main.getBoundingClientRect();
    const k = kopf.getBoundingClientRect();
    if (k.bottom < m.bottom && m.top < k.bottom + 30) return true;
    if (fuss.offsetHeight && m.bottom > fuss.getBoundingClientRect().top - 30) return true;
    return false;
  };
  let groesse = parseFloat(getComputedStyle(h1).fontSize);
  while (zuGross() && groesse > 40) { groesse -= 4; h1.style.fontSize = groesse + 'px'; }
  return true;
})
"""
MAX_VIDEO_MB = 18  # jsDelivr liefert nur Dateien bis ca. 20 MB aus
BERLIN = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def feld(wert):
    return html.escape(str(wert or "")).replace("\n", "<br>")


def relativ(ziel, von):
    return Path(os.path.relpath(ziel, von)).as_posix()


def baue_html(ordner, slide):
    vorlage = slide.get("vorlage", "feed")
    if vorlage not in FORMATE:
        raise ValueError(f"Unbekannte Vorlage '{vorlage}' (erlaubt: {', '.join(FORMATE)})")
    w, h, klasse = FORMATE[vorlage]
    transparent = "transparent" in klasse
    bild = slide.get("bild")
    if bild and not (ordner / bild).exists():
        raise FileNotFoundError(f"Bild '{bild}' fehlt im Post-Ordner")
    logo_datei = BRAND / "logo.png"
    logo_src = relativ(logo_datei, ordner) if logo_datei.exists() else ""
    logo = f'<img src="{logo_src}">' if logo_src else ""
    if slide.get("fuss") == "EVENT":
        fuss = FUSS_EVENT
    elif slide.get("fuss"):
        fuss = f'<div class="pill"><span class="pill-r">{feld(slide["fuss"])}</span></div>'
    else:
        fuss = ""
    ornament = (TEMPLATES / "ornament.svg").read_text(encoding="utf-8")
    deko = "" if transparent else (
        '<div class="punkte"></div>' + ornament.replace("{{ecke}}", "ol") + ornament.replace("{{ecke}}", "ur")
    )
    if logo_src and not bild and not transparent:
        deko += f'<img class="wasserzeichen" src="{logo_src}">'
    akzent = AKZENTE.get(slide.get("akzent", "blau"), AKZENTE["blau"])
    werte = {
        "css": relativ(TEMPLATES / "base.css", ordner),
        "w": str(w),
        "h": str(h),
        "klasse": klasse,
        "akzent_css": f"--akzent: {akzent};",
        "bild_style": f"background-image: url('{bild}')" if bild else "",
        "scrim": '<div class="scrim"></div>' if bild else "",
        "deko": deko,
        "logo": logo,
        "kicker": feld(slide.get("kicker")),
        "titel": feld(slide.get("titel")),
        "text": feld(slide.get("text")),
        "fuss": fuss,
    }
    inhalt = (TEMPLATES / "layout.html").read_text(encoding="utf-8")
    for schluessel, wert in werte.items():
        inhalt = inhalt.replace("{{" + schluessel + "}}", wert)
    return inhalt, w, h, transparent


def render_bild(page, ordner, slide, ziel):
    inhalt, w, h, transparent = baue_html(ordner, slide)
    tmp = ordner / "_render.html"
    tmp.write_text(inhalt, encoding="utf-8")
    png = ziel.with_suffix(".png")
    try:
        page.set_viewport_size({"width": w, "height": h})
        page.goto(tmp.as_uri(), wait_until="networkidle")
        page.evaluate(FIT_JS)
        page.screenshot(path=str(png), omit_background=transparent)
    finally:
        tmp.unlink(missing_ok=True)
    if ziel.suffix == ".jpg":  # Instagram akzeptiert für Bilder nur JPEG
        Image.open(png).convert("RGB").save(ziel, "JPEG", quality=92)
        png.unlink()


def hat_audio(datei):
    ergebnis = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(datei)],
        capture_output=True, text=True,
    )
    return bool(ergebnis.stdout.strip())


def testclip(ziel, dauer):
    """Erzeugt einen Testclip (Farbbalken + Ton) für Tests ohne echtes Material."""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=30:duration={dauer}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={dauer}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(ziel),
    ], check=True)


def render_reel(ordner, reel, overlay, ziel):
    clip = ordner / reel["clip"]
    if reel["clip"] == "__testbild__":
        clip = ziel.parent / "_testclip.mp4"
        testclip(clip, float(reel.get("dauer", 15)))
    if not clip.exists():
        raise FileNotFoundError(f"Clip '{reel['clip']}' fehlt im Post-Ordner")
    dauer = float(reel.get("dauer", 15))
    if not 5 <= dauer <= 90:
        raise ValueError("Reel-Dauer muss zwischen 5 und 90 Sekunden liegen")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(reel.get("start", 0)), "-t", str(dauer), "-i", str(clip)]
    naechster = 1
    if overlay:
        cmd += ["-loop", "1", "-t", str(dauer), "-i", str(overlay)]
        overlay_idx, naechster = naechster, naechster + 1
    if reel.get("audio"):
        audio_datei = ordner / reel["audio"]
        if not audio_datei.exists():
            raise FileNotFoundError(f"Audio '{reel['audio']}' fehlt im Post-Ordner")
        cmd += ["-ss", str(reel.get("audio_start", 0)), "-t", str(dauer), "-i", str(audio_datei)]
        audio, naechster = f"{naechster}:a", naechster + 1
    elif hat_audio(clip):
        audio = "0:a"
    else:
        cmd += ["-f", "lavfi", "-t", str(dauer), "-i", "anullsrc=r=48000:cl=stereo"]
        audio, naechster = f"{naechster}:a", naechster + 1

    filter_v = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1[v0]"
    if overlay:
        hook = reel.get("hook_sekunden")
        enable = f":enable='lte(t,{float(hook)})'" if hook else ""
        filter_v += f";[v0][{overlay_idx}:v]overlay=0:0{enable}[v]"
    else:
        filter_v += ";[v0]null[v]"
    filter_a = f"[{audio}]afade=t=out:st={max(dauer - 1, 0)}:d=1,aresample=48000[a]"
    kbps = min(4000, int(MAX_VIDEO_MB * 8192 / dauer) - 160)

    cmd += [
        "-filter_complex", f"{filter_v};{filter_a}", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-t", str(dauer), str(ziel),
    ]
    subprocess.run(cmd, check=True)
    groesse = ziel.stat().st_size / 1024 / 1024
    if groesse > 19:
        raise ValueError(f"Video ist {groesse:.1f} MB groß, maximal 19 MB möglich – Reel kürzen")


def rendere_post(page, ordner, daten):
    typ = daten.get("typ")
    if typ not in TYPEN:
        raise ValueError(f"Unbekannter Typ '{typ}' (erlaubt: {', '.join(sorted(TYPEN))})")
    zeit(daten["publish_at"])  # prüft das Zeitformat
    slides = daten.get("slides", [])
    reel = daten.get("reel")
    if typ == "karussell" and not 2 <= len(slides) <= 10:
        raise ValueError("Karussell braucht 2 bis 10 Slides")
    if typ == "reel" and not reel:
        raise ValueError("Reel ohne 'reel'-Block")
    if typ in ("bild", "story") and not slides and not reel:
        raise ValueError(f"{typ} braucht 'slides' oder (bei Story) einen 'reel'-Block")

    media = ordner / "media"
    if media.exists():
        shutil.rmtree(media)
    media.mkdir()
    for i, slide in enumerate(slides, 1):
        render_bild(page, ordner, slide, media / f"{i}.jpg")
    if reel:
        overlay = None
        if reel.get("overlay"):
            overlay = media / "overlay.png"
            render_bild(page, ordner, {**reel["overlay"], "vorlage": "overlay"}, overlay)
        render_reel(ordner, reel, overlay, media / "reel.mp4")
        if overlay:
            overlay.unlink()
        (media / "_testclip.mp4").unlink(missing_ok=True)
        # Standbild für VORSCHAU.md (Name ohne Ziffer, wird also nie als Slide gepostet)
        sekunde = float(reel.get("titelbild_sekunde", 1))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(sekunde), "-i", str(media / "reel.mp4"),
                        "-frames:v", "1", "-q:v", "3", str(media / "vorschau.jpg")], check=True)
    (media / ".hash").write_text(medien_hash(ordner, daten))


def schreibe_vorschau(posts):
    stand = datetime.now(BERLIN).strftime("%d.%m.%Y %H:%M")
    zeilen = [
        "# Vorschau: geplante Posts",
        "",
        f"Stand: {stand}. Jeder Post geht frühestens **24 Stunden nach seiner Erstellung** online.",
        "",
        "Posts werden 4 Tage vor ihrem Termin an Buffer übergeben und verschwinden dann von hier.",
        "",
        "**Einspruch:** Solange ein Post hier steht: auf `post.json` tippen → Stift-Symbol → `\"status\": \"geplant\"` in `\"status\": \"stop\"` ändern → *Commit changes*. "
        "Danach: den Post in der **Buffer-App** löschen.",
        "",
    ]
    if not posts:
        zeilen.append("_Aktuell ist nichts geplant._")
    for ordner, daten in posts:
        rel = ordner.relative_to(ROOT).as_posix()
        try:
            t = zeit(daten["publish_at"]).astimezone(BERLIN)
            wann = f"{WOCHENTAGE[t.weekday()]} {t:%d.%m. %H:%M}"
        except (KeyError, ValueError):
            wann = "Zeit fehlt/ungültig"
        zeilen += [f"## {wann} · {daten.get('typ', '?')} · `{ordner.name}`", ""]
        info = f"Status: **{daten.get('status', 'geplant')}**"
        if daten.get("collaborators"):
            info += " · Collab: " + ", ".join("@" + c for c in daten["collaborators"])
        zeilen += [info, ""]
        if daten.get("letzter_fehler"):
            zeilen += [f"⚠️ Fehler: {daten['letzter_fehler']}", ""]
        if daten.get("caption"):
            zeilen += ["> " + z for z in daten["caption"].splitlines()] + [""]
        media = ordner / "media"
        bilder = sorted(media.glob("*.jpg")) if media.exists() else []
        if bilder:
            zeilen.append(" ".join(f'<img src="{rel}/media/{b.name}" width="240">' for b in bilder))
            zeilen.append("")
        links = [f"[post.json bearbeiten]({rel}/post.json)"]
        if (media / "reel.mp4").exists():
            links.insert(0, f"[Reel ansehen]({rel}/media/reel.mp4)")
        zeilen += [" · ".join(links), "", "---", ""]
    (ROOT / "VORSCHAU.md").write_text("\n".join(zeilen), encoding="utf-8")


def main():
    offen = [(o, d) for o, d in lade_posts() if d.get("status", "geplant") in ("geplant", "test")]
    zu_rendern = [(o, d) for o, d in offen if not ist_aktuell(o, d)]
    fehler = 0
    if zu_rendern:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            for ordner, daten in zu_rendern:
                print(f"Rendere {ordner.name} …")
                try:
                    rendere_post(page, ordner, daten)
                    if daten.pop("letzter_fehler", None):
                        speichere(ordner, daten)
                except Exception as e:  # ein kaputter Post soll die anderen nicht blockieren
                    fehler += 1
                    daten["letzter_fehler"] = f"Rendern: {e}"
                    speichere(ordner, daten)
                    print(f"::warning::{ordner.name}: {e}")
            browser.close()
    schreibe_vorschau(lade_posts())
    print(f"{len(zu_rendern) - fehler} Post(s) gerendert, {fehler} Fehler.")


if __name__ == "__main__":
    main()
