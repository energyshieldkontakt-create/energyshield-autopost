#!/usr/bin/env python3
"""Veröffentlicht fällige Posts aus queue/ über die Instagram-API (Instagram Login).

Regeln:
- Ein Post geht frühestens 24 h nach 'erstellt_am' online (Einspruchsfrist).
- Status 'stop' oder 'test' wird nie veröffentlicht.
- Mehr als 12 h verspätete Posts werden nicht mehr gepostet (Status 'verpasst').
- Nach 3 Fehlversuchen: Status 'fehler'.
Erfolgreiche Posts wandern nach posted/.
"""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from common import POSTED, cdn_url, ist_aktuell, jetzt, lade_posts, speichere, zeit

API = f"https://graph.instagram.com/{os.environ.get('IG_API_VERSION') or 'v23.0'}"
TOKEN = os.environ.get("IG_TOKEN", "")
IG_ID = os.environ.get("IG_USER_ID", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
EINSPRUCH = timedelta(hours=24)
MAX_VERSPAETUNG = timedelta(hours=12)
MAX_VERSUCHE = 3


class ApiFehler(Exception):
    pass


def anfrage(methode, pfad, **params):
    params["access_token"] = TOKEN
    daten = urllib.parse.urlencode(params).encode()
    if methode == "GET":
        req = urllib.request.Request(f"{API}/{pfad}?{daten.decode()}")
    else:
        req = urllib.request.Request(f"{API}/{pfad}", data=daten, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as antwort:
            return json.loads(antwort.read())
    except urllib.error.HTTPError as e:
        try:
            meldung = json.loads(e.read()).get("error", {}).get("message", "")
        except ValueError:
            meldung = ""
        raise ApiFehler(f"HTTP {e.code}: {meldung}") from None


def warte_bis_fertig(container_id, max_sekunden=600):
    start = time.time()
    while time.time() - start < max_sekunden:
        status = anfrage("GET", container_id, fields="status_code,status").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            info = anfrage("GET", container_id, fields="status").get("status", "")
            raise ApiFehler(f"Container {status}: {info}")
        time.sleep(10)
    raise ApiFehler("Instagram hat die Medien nicht rechtzeitig verarbeitet")


def container(**params):
    return anfrage("POST", f"{IG_ID}/media", **params)["id"]


def veroeffentliche(ordner, daten):
    typ = daten["typ"]
    media = ordner / "media"
    bilder = sorted(media.glob("*.jpg"), key=lambda p: p.stem)
    bilder = [b for b in bilder if b.stem.isdigit()]
    reel = (media / "reel.mp4").exists()
    extra = {}
    if daten.get("collaborators") and typ != "story":
        extra["collaborators"] = json.dumps(daten["collaborators"][:3])
    caption = daten.get("caption", "")

    if typ == "bild":
        cid = container(image_url=cdn_url(ordner, bilder[0].name), caption=caption, **extra)
    elif typ == "karussell":
        kinder = [container(image_url=cdn_url(ordner, b.name), is_carousel_item="true") for b in bilder]
        for k in kinder:
            warte_bis_fertig(k)
        cid = container(media_type="CAROUSEL", children=",".join(kinder), caption=caption, **extra)
    elif typ == "reel":
        params = dict(media_type="REELS", video_url=cdn_url(ordner, "reel.mp4"), caption=caption, share_to_feed="true", **extra)
        if (media / "cover.jpg").exists():
            params["cover_url"] = cdn_url(ordner, "cover.jpg")
        cid = container(**params)
    elif typ == "story":
        if reel:
            cid = container(media_type="STORIES", video_url=cdn_url(ordner, "reel.mp4"))
        else:
            cid = container(media_type="STORIES", image_url=cdn_url(ordner, bilder[0].name))
    else:
        raise ValueError(f"Unbekannter Typ {typ}")

    warte_bis_fertig(cid)
    media_id = anfrage("POST", f"{IG_ID}/media_publish", creation_id=cid)["id"]
    try:
        permalink = anfrage("GET", media_id, fields="permalink").get("permalink", "")
    except ApiFehler:
        permalink = ""
    return media_id, permalink


def main():
    if not DRY_RUN and not (TOKEN and IG_ID):
        sys.exit("IG_TOKEN und IG_USER_ID fehlen (GitHub → Settings → Secrets and variables → Actions).")
    nun = jetzt()
    fehler = 0
    for ordner, daten in lade_posts():
        status = daten.get("status", "geplant")
        if status != "geplant":
            continue
        try:
            geplant = zeit(daten["publish_at"])
            erstellt = zeit(daten["erstellt_am"])
        except (KeyError, ValueError) as e:
            daten["status"], daten["letzter_fehler"] = "fehler", f"Zeitangabe fehlt/ungültig: {e}"
            speichere(ordner, daten)
            continue
        faellig = max(geplant, erstellt + EINSPRUCH)
        if nun < faellig:
            continue
        if nun - faellig > MAX_VERSPAETUNG:
            daten["status"], daten["letzter_fehler"] = "verpasst", f"Nicht gepostet, mehr als 12 h verspätet (fällig {faellig:%d.%m. %H:%M} UTC)"
            speichere(ordner, daten)
            print(f"::warning::{ordner.name}: verpasst")
            continue
        if not ist_aktuell(ordner, daten):
            print(f"::warning::{ordner.name}: Medien fehlen oder sind veraltet – Workflow 'Rendern' prüfen")
            continue

        print(f"{'[Testlauf] ' if DRY_RUN else ''}Poste {ordner.name} ({daten['typ']}) …")
        if DRY_RUN:
            continue
        try:
            media_id, permalink = veroeffentliche(ordner, daten)
        except Exception as e:
            fehler += 1
            daten["versuche"] = daten.get("versuche", 0) + 1
            daten["letzter_fehler"] = str(e)
            if daten["versuche"] >= MAX_VERSUCHE:
                daten["status"] = "fehler"
            speichere(ordner, daten)
            print(f"::error::{ordner.name}: {e}")
            continue
        daten["status"] = "gepostet"
        daten["ergebnis"] = {"media_id": media_id, "permalink": permalink, "gepostet_am": jetzt().isoformat()}
        daten.pop("letzter_fehler", None)
        speichere(ordner, daten)
        POSTED.mkdir(exist_ok=True)
        shutil.move(str(ordner), str(POSTED / ordner.name))
        print(f"Gepostet: {permalink or media_id}")
    if fehler:
        sys.exit(1)


if __name__ == "__main__":
    main()
