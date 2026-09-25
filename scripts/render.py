#!/usr/bin/env python3
"""Rendert Grafiken (HTML -> JPEG) und Reels (ffmpeg) für alle Posts in queue/.

Läuft in GitHub Actions. Rendert nur Posts, deren Inhalt sich seit dem letzten
Rendern geändert hat, und schreibt danach VORSCHAU.md neu.
"""
import html
import os
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image
from playwright.sync_api import sync_playwright

from common import BRAND, ROOT, TEMPLATES, TYPEN, ist_aktuell, lade_posts, medien_hash, speichere, zeit
from trackid import UNBEKANNT, tracks_im_fenster, zeitleiste

# Vorlage -> (Breite, Höhe, CSS-Klassen)
FORMATE = {
    "feed": (1080, 1350, "feed"),
    "lineup": (1080, 1350, "lineup"),
    "story": (1080, 1920, "story"),
    "countdown": (1080, 1920, "countdown"),
    "overlay": (1080, 1920, "overlay transparent"),
    "cover": (1080, 1080, "cover"),  # Shield-Sessions-Cover, eigene Vorlage cover.html
    "quadrat": (1080, 1080, "feed quadrat"),  # quadratische Slide, z. B. DJ-Vorstellung im Shield-Sessions-Karussell
}
# Farben aus den bisherigen Flyern: Cyan-Neon (Standard), Mint (Talent Night), Violett; dazu Orange und Pink
AKZENTE = {"blau": "#2EE6F5", "liquid": "#6FF5C2", "neuro": "#9D7BFF", "jumpup": "#FF9A3C", "halftime": "#FF4FA3"}
# Shield Sessions: Akzentfarbe nach dem ersten Stil des Mixes
STIL_AKZENT = {"deep": "blau", "liquid": "liquid", "neurofunk": "neuro", "neuro": "neuro",
               "jump-up": "jumpup", "jumpup": "jumpup", "halftime": "halftime"}
# Shield Sessions: jeder Resident hat ein eigenes Schild (templates/schilde/) und ein Kürzel; alle anderen bekommen "standard"
RESIDENTS = {"kruxer": ("kruxer", "KRX"), "stone d": ("stoned", "STD"), "jhinx": ("jhinx", "JHX"), "ranj": ("ranj", "RNJ")}
# Fußbereich im Flyer-Stil: Info-Leiste, darunter Datum und drei Infos, getrennt durch Leuchtlinien
FUSS_EVENT = (
    '<div class="eventfuss">'
    '<div class="pill"><span class="pill-l">Drum and Bass</span><span class="pill-r">Nur 120 Plätze</span></div>'
    '<div class="infogrid">'
    '<div class="zelle breit"><span class="datum">SA 30.01.27</span></div>'
    '<div class="zelle"><span class="wert">Club Bastion<br>Kirchheim</span></div>'
    '<div class="zelle"><span class="wert">Nur<br>Abendkasse</span></div>'
    '<div class="zelle"><span class="wert">Ab 18<br>Jahren</span></div>'
    '</div></div>'
)
# Verkleinert die Headline, bis sie in die Breite passt und weder Kopf noch Fuß berührt
FIT_JS = """
document.fonts.ready.then(() => {
  const h1 = document.querySelector('h1[data-fit]');
  const main = document.querySelector('main');
  const kopf = document.querySelector('.marke');
  const fuss = document.querySelector('footer');
  if (!h1 || !h1.textContent.trim()) return true;
  // Breite nur des Textes messen (ohne Glitch-Pseudoelemente, die absichtlich überstehen)
  const breit = () => { const r = document.createRange(); r.selectNodeContents(h1); return r.getBoundingClientRect().width > h1.clientWidth + 1; };
  if (!main) {  // Cover: nur in die Breite einpassen
    let g = parseFloat(getComputedStyle(h1).fontSize);
    while (breit() && g > 40) { g -= 4; h1.style.fontSize = g + 'px'; }
    return true;
  }
  // Hauptblock mittig in den freien Raum zwischen Schriftzug und Fuß setzen
  if (fuss.offsetHeight && !document.body.classList.contains('overlay')) {
    const kUnten = kopf.getBoundingClientRect().bottom, fOben = fuss.getBoundingClientRect().top;
    if (document.body.classList.contains('foto')) main.style.bottom = (innerHeight - fOben + 40) + 'px';
    else main.style.top = ((kUnten + fOben) / 2) + 'px';
  }
  const zuGross = () => {
    if (breit()) return true;
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
TRENNER = ' <span class="x">X</span> '  # zwischen mehreren Track-IDs an einem Cue
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
    if vorlage == "cover":
        return baue_cover(ordner, slide, w, h)
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
        "klasse": klasse + (" foto" if bild else ""),
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


def baue_cover(ordner, slide, w, h):
    """Shield-Sessions-Cover: Schild-Emblem mit Logo und VOL.-Nummer, DJ-Name, Stil."""
    for pflicht in ("dj", "vol", "stil"):
        if not slide.get(pflicht):
            raise ValueError(f"Cover braucht '{pflicht}'")
    stile = [s.strip() for s in str(slide["stil"]).replace("·", ",").split(",") if s.strip()]
    akzent = slide.get("akzent") or STIL_AKZENT.get(stile[0].lower(), "blau")
    logo_datei = BRAND / "logo.png"
    ornament = (TEMPLATES / "ornament.svg").read_text(encoding="utf-8")
    deko = '<div class="punkte"></div>' + "".join(ornament.replace("{{ecke}}", e) for e in ("ol", "ur", "ul", "ur2"))
    schild_name, code = RESIDENTS.get(str(slide["dj"]).strip().lower(), ("standard", str(slide["dj"])[:3].upper()))
    schild = (TEMPLATES / "schilde" / f"{schild_name}.svg").read_text(encoding="utf-8")
    werte = {
        "css": relativ(TEMPLATES / "base.css", ordner),
        "w": str(w),
        "h": str(h),
        "akzent_css": f"--akzent: {AKZENTE.get(akzent, AKZENTE['blau'])};",
        "deko": deko,
        "logo": f'<img src="{relativ(logo_datei, ordner)}">' if logo_datei.exists() else "",
        "vol": f"{int(slide['vol']):02d}",
        "dj": feld(slide["dj"]),
        "stil": " · ".join(feld(s) for s in stile),
        "schild": schild,
        "schild_klasse": f"schild-{schild_name}",
        "resident_code": code,
    }
    inhalt = (TEMPLATES / "cover.html").read_text(encoding="utf-8")
    for schluessel, wert in werte.items():
        inhalt = inhalt.replace("{{" + schluessel + "}}", wert)
    return inhalt, w, h, False


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


def mmss(sekunden):
    sekunden = int(round(sekunden))
    return f"{sekunden // 3600}:{sekunden % 3600 // 60:02d}:{sekunden % 60:02d}" if sekunden >= 3600 else f"{sekunden // 60}:{sekunden % 60:02d}"


def audio_laenge(datei):
    ergebnis = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(datei)],
                              capture_output=True, text=True, check=True)
    return float(ergebnis.stdout.strip())


def sekunden(zeitangabe):
    """ "3:05" -> 185, "1:02:30" -> 3750"""
    teile = [int(t) for t in str(zeitangabe).strip().split(":")]
    return sum(t * 60 ** i for i, t in enumerate(reversed(teile)))


MIX_URL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"


def lade_mix(drive_id):
    """Lädt den ganzen Mix aus der Google Drive. Der Ordner muss per Link freigegeben sein (Betrachter)."""
    ziel = Path(tempfile.gettempdir()) / f"mix_{drive_id}"
    if ziel.exists():
        return ziel
    anfrage = urllib.request.Request(MIX_URL.format(drive_id), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(anfrage, timeout=900) as antwort:
        if "text/html" in antwort.headers.get("Content-Type", ""):
            raise RuntimeError("Mix nicht ladbar – ist der Drive-Ordner „Shield Sessions“ per Link freigegeben (Jeder mit dem Link: Betrachter)?")
        with open(ziel, "wb") as f:
            shutil.copyfileobj(antwort, f)
    return ziel


def baue_hoerprobe(ordner, cover, nr, anzahl, dauer, ab, tracks=None):
    """Hintergrund eines Hörproben-Videos: Cover, DJ, Stil, BPM, Hot-Cue-Pad (Wellenform kommt danach per ffmpeg)."""
    stile = [s.strip() for s in str(cover["stil"]).replace("·", ",").split(",") if s.strip()]
    akzent = cover.get("akzent") or STIL_AKZENT.get(stile[0].lower(), "blau")
    ornament = (TEMPLATES / "ornament.svg").read_text(encoding="utf-8")
    bpm = cover.get("bpm")
    werte = {
        "css": relativ(TEMPLATES / "base.css", ordner),
        "w": "1080", "h": "1080",
        "akzent_css": f"--akzent: {AKZENTE.get(akzent, AKZENTE['blau'])};",
        "deko": '<div class="punkte"></div>' + "".join(ornament.replace("{{ecke}}", e) for e in ("ol", "ur", "ul", "ur2")),
        "cover": "media/1.jpg",
        "vol": f"{int(cover['vol']):02d}",
        "dj": feld(cover["dj"]),
        "stil": " · ".join(feld(s) for s in stile),
        "bpm": f'<span class="hp-bpm"><b>{feld(bpm)}</b>BPM</span>' if bpm else "",
        "cue": "ABCDEFGH"[nr - 1],
        "nr": str(nr), "anzahl": str(anzahl),
        "zeit": mmss(ab), "zeit_ende": mmss(ab + dauer),
        "tracks": TRENNER.join(f'<span class="id">{feld(t)}</span>' if t == UNBEKANNT else feld(t) for t in (tracks or [UNBEKANNT])),
    }
    inhalt = (TEMPLATES / "hoerprobe.html").read_text(encoding="utf-8")
    for schluessel, wert in werte.items():
        inhalt = inhalt.replace("{{" + schluessel + "}}", wert)
    return inhalt


# Wellenform im CDJ/rekordbox-Look: Bässe blau, Mitten orange, Höhen weiß; Feld 940 x 240 bei x 70 / y 584
WELLE_X, WELLE_Y, WELLE_B, WELLE_H = 70, 584, 940, 240
WELLE_FILTER = (
    "[0:a]aformat=channel_layouts=mono,asplit=3[l][m][h];"
    f"[l]lowpass=f=180,showwavespic=s={WELLE_B}x{WELLE_H}:colors=0x1F6FFF:scale=sqrt[wl];"
    f"[m]highpass=f=180,lowpass=f=2500,showwavespic=s={WELLE_B}x{WELLE_H}:colors=0xFFA235:scale=sqrt[wm];"
    f"[h]highpass=f=2500,showwavespic=s={WELLE_B}x{WELLE_H}:colors=0xF4F4F4:scale=sqrt[wh];"
    f"color=c=black:s={WELLE_B}x{WELLE_H}:d=1[s];[s][wl]overlay[a1];[a1][wm]overlay[a2];[a2][wh]overlay,format=rgb24,split[voll][v2];"
    "[v2]colorchannelmixer=rr=.3:gg=.3:bb=.3[dunkel]"
)


def render_hoerprobe(page, ordner, cover, hp, nr, anzahl, ziel, mix=None, segmente=None):
    """Video-Slide: Hintergrund + CDJ-Wellenform (gespielt hell, offen abgedunkelt) + Abspielkopf + Ton."""
    if hp.get("audio") == "__testton__":  # nur für Tests: Kick + Hi-Hat bei 174 BPM
        audio, start = ziel.parent / "_testton.wav", 0.0
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "aevalsrc='0.7*sin(2*PI*50*t)*exp(-9*mod(t,0.345))*(0.6+0.4*sin(2*PI*t/8))"
                        "+0.25*(random(0)-0.5)*exp(-30*mod(t+0.1725,0.345))':s=44100:d=30",
                        str(audio)], check=True)
    elif hp.get("audio"):  # fertige Hörprobe im Post-Ordner
        audio, start = ordner / hp["audio"], float(hp.get("start", 0))
    elif mix:  # direkt aus dem ganzen Mix ab der Stelle "im_mix"
        audio, start = mix, float(sekunden(hp["im_mix"]))
    else:
        raise ValueError("Hörprobe braucht 'audio' oder einen Mix ('mix_drive_id')")
    if not audio.exists():
        raise FileNotFoundError(f"Hörprobe '{hp.get('audio')}' fehlt im Post-Ordner")
    dauer = min(float(hp.get("dauer", 30)), audio_laenge(audio) - start, 59)
    if dauer < 5:
        raise ValueError(f"Hörprobe {nr} ist kürzer als 5 Sekunden (Zeitstempel hinter dem Mix-Ende?)")
    ab = sekunden(hp["im_mix"]) if hp.get("im_mix") else 0
    tmp, bg = ordner / "_render.html", ziel.parent / "_hp_bg.png"
    tracks = hp.get("tracks") or (tracks_im_fenster(segmente, ab, dauer) if segmente else [UNBEKANNT])
    tmp.write_text(baue_hoerprobe(ordner, cover, nr, anzahl, dauer, ab, tracks), encoding="utf-8")
    try:
        page.set_viewport_size({"width": 1080, "height": 1080})
        page.goto(tmp.as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.screenshot(path=str(bg))
    finally:
        tmp.unlink(missing_ok=True)
    voll, dunkel = ziel.parent / "_hp_voll.png", ziel.parent / "_hp_dunkel.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(dauer), "-i", str(audio),
                    "-filter_complex", WELLE_FILTER, "-map", "[voll]", "-frames:v", "1", str(voll),
                    "-map", "[dunkel]", "-frames:v", "1", str(dunkel)], check=True)
    d = f"{dauer:.3f}"
    filter_v = (
        "[1:v]format=gbrp[g];[2:v]format=gbrp[a];"
        f"[g][a]blend=all_expr='if(gte(X,W*T/{d}),A,B)',format=yuv420p[w];"
        f"color=c=white:s=3x{WELLE_H + 16}:r=30[k];"
        f"[0:v][w]overlay={WELLE_X}:{WELLE_Y}[b];"
        f"[b][k]overlay=x='{WELLE_X}+{WELLE_B - 3}*t/{d}':y={WELLE_Y - 8}:eval=frame:shortest=1,format=yuv420p[v];"
        f"[3:a]afade=t=in:d=0.4,afade=t=out:st={max(dauer - 0.8, 0):.3f}:d=0.8,aresample=48000[au]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "30", "-t", d, "-i", str(bg),
        "-loop", "1", "-framerate", "30", "-t", d, "-i", str(dunkel),
        "-loop", "1", "-framerate", "30", "-t", d, "-i", str(voll),
        "-ss", str(start), "-t", d, "-i", str(audio),
        "-filter_complex", filter_v, "-map", "[v]", "-map", "[au]",
        "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p", "-b:v", "3000k",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-t", d, str(ziel),
    ], check=True)
    for datei in (bg, voll, dunkel, ziel.parent / "_testton.wav"):
        datei.unlink(missing_ok=True)


def rendere_post(page, page_hd, ordner, daten):
    typ = daten.get("typ")
    if typ not in TYPEN:
        raise ValueError(f"Unbekannter Typ '{typ}' (erlaubt: {', '.join(sorted(TYPEN))})")
    zeit(daten["publish_at"])  # prüft das Zeitformat
    slides = daten.get("slides", [])
    reel = daten.get("reel")
    hoerproben = daten.get("hoerproben", [])
    if typ == "karussell" and not 2 <= len(slides) + len(hoerproben) <= 10:
        raise ValueError("Karussell braucht 2 bis 10 Slides (inklusive Hörproben)")
    if hoerproben and (typ != "karussell" or not slides or slides[0].get("vorlage") != "cover"):
        raise ValueError("Hörproben gibt es nur im Karussell mit einem Cover als erster Slide")
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
        if slide.get("vorlage") == "cover":  # große Fassung für SoundCloud (ohne Ziffer, wird nicht gepostet)
            render_bild(page_hd, ordner, slide, media / "soundcloud.jpg")
    mix = lade_mix(daten["mix_drive_id"]) if daten.get("mix_drive_id") and any(not hp.get("audio") for hp in hoerproben) else None
    # Track-IDs: einmal pro Mix per Shazam + Tracklist ermitteln und in der post.json merken
    segmente = daten.get("trackid")
    if hoerproben and segmente is None and mix and not all(hp.get("tracks") for hp in hoerproben):
        print(f"  Track-Erkennung für {ordner.name} …")
        segmente = zeitleiste(mix, audio_laenge(mix), daten.get("tracklist"))
        if any(name != UNBEKANNT for _, name in segmente):  # Fehlschläge nicht dauerhaft merken
            daten["trackid"] = segmente
            speichere(ordner, daten)
    if segmente:  # Tracklist mit Zeitstempeln, z. B. für die SoundCloud-Beschreibung (wird nicht gepostet)
        (media / "tracklist.txt").write_text("\n".join(f"{mmss(s)} {name}" for s, name in segmente) + "\n", encoding="utf-8")
    for i, hp in enumerate(hoerproben, 1):
        render_hoerprobe(page, ordner, slides[0], hp, i, len(hoerproben), media / f"{len(slides) + i}.mp4", mix, segmente)
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
        if media.exists():
            videos = sorted((v for v in media.glob("*.mp4") if v.stem.isdigit()), key=lambda v: int(v.stem))
            links[:0] = [f"[Video-Slide {v.stem} ansehen]({rel}/media/{v.name})" for v in videos]
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
            page_hd = browser.new_page(device_scale_factor=2)  # SoundCloud-Cover in 2160 px
            for ordner, daten in zu_rendern:
                print(f"Rendere {ordner.name} …")
                try:
                    rendere_post(page, page_hd, ordner, daten)
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
