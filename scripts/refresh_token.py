#!/usr/bin/env python3
"""Verlängert den Instagram-Token (gilt sonst nur 60 Tage).

Schreibt den neuen Token nach neuer_token.txt, damit der Workflow ihn per
`gh secret set` speichern kann. Die Datei wird danach sofort gelöscht.
"""
import json
import os
import urllib.parse
import urllib.request

alt = os.environ["IG_TOKEN"]
url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": alt}
)
with urllib.request.urlopen(url, timeout=60) as antwort:
    daten = json.loads(antwort.read())

neu = daten["access_token"]
tage = int(daten.get("expires_in", 0)) // 86400
print(f"::add-mask::{neu}")
print(f"Token verlängert, gültig für weitere {tage} Tage.")
with open("neuer_token.txt", "w") as f:
    f.write(neu)
with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"geaendert={'ja' if neu != alt else 'nein'}\n")
