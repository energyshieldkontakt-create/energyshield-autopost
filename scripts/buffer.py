#!/usr/bin/env python3
"""Übergibt fällige Posts aus queue/ an Buffer, das sie pünktlich auf Instagram veröffentlicht.

Regeln:
- Übergabe frühestens 24 h nach 'erstellt_am' (Einspruchsfrist über VORSCHAU.md).
- Übergabe erst, wenn der Post in den nächsten 4 Tagen dran ist (Buffer Free: max. 10 geplante Posts).
- Status 'stop' oder 'test' wird nie übergeben.
- Ist die Zeit schon (fast) vorbei, ohne dass übergeben wurde: Status 'verpasst'.
- Nach 3 Fehlversuchen: Status 'fehler'.
Übergebene Posts wandern nach posted/. Einspruch danach: Post in der Buffer-App löschen.
"""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import timedelta, timezone

from common import POSTED, cdn_url, ist_aktuell, jetzt, lade_posts, speichere, zeit

API = "https://api.buffer.com"
KEY = os.environ.get("BUFFER_API_KEY", "").strip()


def pruefe_schluessel():
    """Bricht mit verständlicher Meldung ab, wenn der Schlüssel fehlt oder offensichtlich falsch ist.
    Gibt nie den Schlüssel selbst aus, nur Länge, Sonderzeichen und die letzten 4 Zeichen
    (die Buffer ohnehin offen anzeigt)."""
    if not KEY:
        sys.exit("BUFFER_API_KEY fehlt (GitHub → Settings → Secrets and variables → Actions).")
    fremd = sorted({c for c in KEY if not c.isascii()})
    if fremd:
        ende = KEY[-4:] if KEY[-4:].isascii() else "?"
        sys.exit(f"BUFFER_API_KEY enthält ungültige Zeichen {fremd} (Länge {len(KEY)}, endet auf '{ende}'). "
                 "Vermutlich wurde die verdeckte Anzeige kopiert statt des Schlüssels. "
                 "Neuen Schlüssel erstellen und direkt aus dem Erstell-Fenster kopieren.")
KANAL = os.environ.get("BUFFER_CHANNEL_ID", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
EINSPRUCH = timedelta(hours=24)
VORLAUF = timedelta(days=4)
MIN_ABSTAND = timedelta(minutes=15)
MAX_VERSUCHE = 3
INSTAGRAM_TYP = {"bild": "post", "karussell": "post", "reel": "reel", "story": "story"}

CREATE_POST = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id } }
    ... on MutationError { message }
  }
}
"""


def graphql(query, variablen=None):
    daten = json.dumps({"query": query, "variables": variablen or {}}).encode()
    req = urllib.request.Request(
        API, data=daten, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as antwort:
            ergebnis = json.loads(antwort.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Buffer HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from None
    if ergebnis.get("errors"):
        raise RuntimeError("Buffer: " + "; ".join(f.get("message", "") for f in ergebnis["errors"]))
    return ergebnis["data"]


def instagram_kanal():
    """Findet den Instagram-Kanal im Buffer-Konto (oder nimmt BUFFER_CHANNEL_ID)."""
    if KANAL:
        return KANAL
    gefunden = []
    for org in graphql("query { account { organizations { id } } }")["account"]["organizations"]:
        abfrage = "query { channels(input: {organizationId: %s}) { id service name } }" % json.dumps(org["id"])
        gefunden += [k for k in graphql(abfrage)["channels"] if k["service"] == "instagram"]
    if len(gefunden) != 1:
        namen = ", ".join(f"{k['name']} ({k['id']})" for k in gefunden) or "keiner"
        raise RuntimeError(f"Genau ein Instagram-Kanal erwartet, gefunden: {namen}. Sonst BUFFER_CHANNEL_ID setzen.")
    print(f"Instagram-Kanal in Buffer: {gefunden[0]['name']}")
    return gefunden[0]["id"]


def aufwaermen(url, max_sekunden=90):
    """Ruft die Datei ab, bis sie erreichbar ist (jsDelivr lädt beim ersten Abruf erst von GitHub)."""
    start = time.time()
    while True:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=60) as antwort:
                antwort.read()
                return
        except (urllib.error.URLError, TimeoutError) as e:
            if time.time() - start > max_sekunden:
                raise RuntimeError(f"Datei nicht erreichbar: {url} ({e})") from None
            time.sleep(5)


def an_buffer(kanal, ordner, daten, geplant, versuch=1):
    typ = daten["typ"]
    media = ordner / "media"
    if (media / "reel.mp4").exists():
        video = {"url": cdn_url(ordner, "reel.mp4")}
        sekunde = (daten.get("reel") or {}).get("titelbild_sekunde")
        if sekunde is not None:
            video["metadata"] = {"thumbnailOffset": int(float(sekunde) * 1000)}
        assets = [{"video": video}]
    else:
        # Slides in Reihenfolge 1, 2, 3 …; Bilder (.jpg) und Video-Slides (.mp4, z. B. Hörproben) gemischt
        teile = sorted((m for m in media.iterdir() if m.stem.isdigit() and m.suffix in (".jpg", ".mp4")), key=lambda m: int(m.stem))
        assets = [{"video" if m.suffix == ".mp4" else "image": {"url": cdn_url(ordner, m.name)}} for m in teile]
    ig_typ = INSTAGRAM_TYP[typ]
    eingabe = {
        "channelId": kanal,
        "text": "" if typ == "story" else daten.get("caption", ""),
        "schedulingType": "automatic",
        "mode": "customScheduled",
        "dueAt": geplant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "assets": assets,
        "metadata": {"instagram": {"type": ig_typ, "shouldShareToFeed": ig_typ != "story"}},
    }
    for asset in assets:
        aufwaermen(next(iter(asset.values()))["url"])
    antwort = graphql(CREATE_POST, {"input": eingabe})["createPost"]
    if "post" not in antwort:
        meldung = antwort.get("message", "unbekannter Fehler")
        if "could not be read" in meldung and versuch < 2:
            time.sleep(30)
            return an_buffer(kanal, ordner, daten, geplant, versuch + 1)
        raise RuntimeError(f"Buffer: {meldung}")
    return antwort["post"]["id"]


DELETE_POST = """
mutation DeletePost($input: DeletePostInput!) {
  deletePost(input: $input) {
    ... on DeletePostSuccess { id }
    ... on VoidMutationError { message }
  }
}
"""


def testpost():
    """Legt die Test-Posts (status 'test') 30 Tage in der Zukunft in Buffer an und löscht sie sofort wieder."""
    pruefe_schluessel()
    kanal = instagram_kanal()
    tests = [(o, d) for o, d in lade_posts() if d.get("status") == "test"]
    if not tests:
        sys.exit("Keine Test-Posts (status 'test') in queue/ gefunden.")
    fehler = 0
    for ordner, daten in tests:
        if not ist_aktuell(ordner, daten):
            print(f"::warning::{ordner.name}: Medien fehlen – erst 'Rendern' laufen lassen")
            fehler += 1
            continue
        try:
            buffer_id = an_buffer(kanal, ordner, daten, jetzt() + timedelta(days=30))
            print(f"OK {ordner.name} ({daten['typ']}): in Buffer angelegt ({buffer_id})")
        except Exception as e:
            print(f"::error::{ordner.name} ({daten['typ']}): {e}")
            fehler += 1
            continue
        antwort = graphql(DELETE_POST, {"input": {"id": buffer_id}})["deletePost"]
        if "id" in antwort:
            print(f"   … und wieder gelöscht.")
        else:
            print(f"::error::Test-Post {buffer_id} konnte nicht gelöscht werden: {antwort.get('message')} – bitte in Buffer löschen")
            fehler += 1
    if fehler:
        sys.exit(1)


def main():
    if os.environ.get("TESTPOST") == "1":
        return testpost()
    if KEY and DRY_RUN:  # Testlauf mit Schlüssel = Verbindungstest
        pruefe_schluessel()
        instagram_kanal()
    nun = jetzt()
    kanal = None
    fehler = 0
    for ordner, daten in lade_posts():
        if daten.get("status", "geplant") != "geplant":
            continue
        try:
            geplant = zeit(daten["publish_at"])
            erstellt = zeit(daten["erstellt_am"])
        except (KeyError, ValueError) as e:
            daten["status"], daten["letzter_fehler"] = "fehler", f"Zeitangabe fehlt/ungültig: {e}"
            speichere(ordner, daten)
            continue
        if geplant - nun < MIN_ABSTAND:
            daten["status"] = "verpasst"
            daten["letzter_fehler"] = "Nicht rechtzeitig an Buffer übergeben (Einspruchsfrist oder Fehler)"
            speichere(ordner, daten)
            print(f"::warning::{ordner.name}: verpasst")
            continue
        if nun < erstellt + EINSPRUCH or geplant - nun > VORLAUF:
            continue
        if not ist_aktuell(ordner, daten):
            print(f"::warning::{ordner.name}: Medien fehlen oder sind veraltet – Workflow 'Rendern' prüfen")
            continue

        print(f"{'[Testlauf] ' if DRY_RUN else ''}Übergebe {ordner.name} ({daten['typ']}) an Buffer …")
        if DRY_RUN:
            continue
        pruefe_schluessel()  # erst prüfen, wenn wirklich etwas fällig ist
        try:
            kanal = kanal or instagram_kanal()
            buffer_id = an_buffer(kanal, ordner, daten, geplant)
        except Exception as e:
            fehler += 1
            daten["versuche"] = daten.get("versuche", 0) + 1
            daten["letzter_fehler"] = str(e)
            if daten["versuche"] >= MAX_VERSUCHE:
                daten["status"] = "fehler"
            speichere(ordner, daten)
            print(f"::error::{ordner.name}: {e}")
            continue
        daten["status"] = "bei_buffer"
        daten["ergebnis"] = {"buffer_id": buffer_id, "uebergeben_am": jetzt().isoformat()}
        daten.pop("letzter_fehler", None)
        speichere(ordner, daten)
        POSTED.mkdir(exist_ok=True)
        shutil.move(str(ordner), str(POSTED / ordner.name))
        print(f"An Buffer übergeben: {buffer_id}")
        if daten.get("collaborators"):
            print(f"::notice::{ordner.name}: Collab manuell einladen nach dem Posten: "
                  + ", ".join("@" + c for c in daten["collaborators"]))
    if fehler:
        sys.exit(1)


if __name__ == "__main__":
    main()
