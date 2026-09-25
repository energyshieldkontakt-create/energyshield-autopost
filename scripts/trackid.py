"""Track-IDs für Shield Sessions: erkennt Tracks im Mix per Shazam (Bibliothek shazamio, kostenlos, inoffiziell)
und verbindet das Ergebnis mit der Tracklist des DJs (ohne Zeiten). Ergebnis: Zeitleiste [(start_sekunde, name)].

- Alle SCHRITT Sekunden wird ein Ausschnitt von LAENGE Sekunden an Shazam geschickt.
- Erkannte Titel werden der Tracklist zugeordnet (unscharfer Vergleich). Nicht erkannte Tracks der Liste werden
  anhand der Reihenfolge in die Lücken zwischen erkannten Tracks verteilt.
- Wo nichts bekannt ist, steht „ID – ID“.
"""
import asyncio
import difflib
import re
import subprocess
import tempfile
from pathlib import Path

SCHRITT, LAENGE = 20, 12
UNBEKANNT = "ID – ID"


def _norm(text):
    text = text.lower()
    text = re.sub(r"\(.*?\)|\[.*?\]|feat\.?.*?(?=-|–|$)|ft\.?.*?(?=-|–|$)", " ", text)
    return re.sub(r"[^a-z0-9äöüß]+", " ", text).strip()


def _passt(a, b):
    a, b = _norm(a), _norm(b)
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6 or (len(b) > 4 and b in a) or (len(a) > 4 and a in b)


async def _scan(mix, dauer):
    from shazamio import Shazam
    shazam = Shazam()
    treffer = []
    with tempfile.TemporaryDirectory() as tmp:
        for t in range(0, max(int(dauer) - LAENGE, 1), SCHRITT):
            stueck = Path(tmp) / f"{t}.ogg"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-t", str(LAENGE), "-i", str(mix),
                            "-ac", "1", "-ar", "44100", str(stueck)], check=True)
            try:
                erkennen = getattr(shazam, "recognize", None) or shazam.recognize_song
                antwort = await erkennen(str(stueck))
            except Exception as e:  # einzelne Aussetzer ignorieren
                print(f"  Shazam bei {t}s: {e}")
                antwort = {}
            track = (antwort or {}).get("track") or {}
            if track.get("title"):
                treffer.append((t, f"{track.get('subtitle', '').strip()} – {track['title'].strip()}".strip(" –")))
            await asyncio.sleep(0.6)
    return treffer


def zeitleiste(mix, dauer, tracklist=None):
    """Liefert [(start, name), …] über den ganzen Mix, sortiert. Wirft keine Fehler nach außen."""
    tracklist = [t.strip() for t in (tracklist or []) if t.strip()]
    try:
        treffer = asyncio.run(_scan(mix, dauer))
    except Exception as e:
        print(f"::warning::Track-Erkennung nicht möglich: {e}")
        treffer = []
    print(f"  Shazam: {len(treffer)} Treffer")

    # Treffer -> (zeit, schluessel, anzeige); schluessel = Index in der Tracklist oder eigener Name
    runs = []  # [schluessel, anzeige, erster, letzter]
    for t, name in treffer:
        idx = next((i for i, eintrag in enumerate(tracklist) if _passt(name, eintrag)), None)
        schluessel, anzeige = (idx, tracklist[idx]) if idx is not None else (_norm(name), name)
        if runs and runs[-1][0] == schluessel:
            runs[-1][3] = t
        else:
            runs.append([schluessel, anzeige, t, t])

    # Einzelne Ausreißer mitten in einem anderen Track entfernen (A, B, A -> A)
    bereinigt = []
    for i, run in enumerate(runs):
        if 0 < i < len(runs) - 1 and run[2] == run[3] and runs[i - 1][0] == runs[i + 1][0]:
            continue
        if bereinigt and bereinigt[-1][0] == run[0]:
            bereinigt[-1][3] = run[3]
        else:
            bereinigt.append(run)
    runs = bereinigt

    segmente = []  # (start, name)

    def fuelle(von, bis, namen):
        """Verteilt fehlende Tracks gleichmäßig auf eine Lücke."""
        schritt = max((bis - von) / len(namen), 1)
        for k, name in enumerate(namen):
            segmente.append((von + k * schritt, name))

    erkannt = {r[0] for r in runs if isinstance(r[0], int)}
    cursor, letzter_idx = 0, -1
    for schluessel, anzeige, erster, letzter in runs:
        fehlend = []
        if isinstance(schluessel, int):
            fehlend = [tracklist[i] for i in range(letzter_idx + 1, schluessel) if i not in erkannt]
            letzter_idx = max(letzter_idx, schluessel)
        if fehlend:
            fuelle(cursor, erster, fehlend)
        elif erster - cursor > 45:
            segmente.append((cursor, UNBEKANNT))
        segmente.append((erster, anzeige))
        cursor = letzter + LAENGE
    rest = [tracklist[i] for i in range(letzter_idx + 1, len(tracklist)) if i not in erkannt]
    if rest:
        fuelle(cursor, dauer, rest)
    elif dauer - cursor > 45:
        segmente.append((cursor, UNBEKANNT))
    segmente.sort()
    if not segmente or segmente[0][0] >= 45:
        segmente.insert(0, (0, UNBEKANNT))
    else:
        segmente[0] = (0, segmente[0][1])
    return [(round(s), n) for s, n in segmente]


def tracks_im_fenster(segmente, start, dauer, rand=3):
    """Namen aller Tracks, die zwischen start und start+dauer laufen (Übergänge -> mehrere)."""
    namen = []
    for i, (s, name) in enumerate(segmente):
        ende = segmente[i + 1][0] if i + 1 < len(segmente) else float("inf")
        if s < start + dauer - rand and ende > start + rand and name not in namen:
            namen.append(name)
    return namen or [UNBEKANNT]
