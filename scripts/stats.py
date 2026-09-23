#!/usr/bin/env python3
"""Hängt die Instagram-Wochenzahlen an stats/zahlen.csv an (für Montags-Briefing und Tracking)."""
import csv
from datetime import timedelta

from common import ROOT, jetzt
from publish import IG_ID, ApiFehler, anfrage

DATEI = ROOT / "stats" / "zahlen.csv"
SPALTEN = ["datum", "follower", "beitraege", "reichweite_7t", "profilaufrufe_7t", "interagierende_7t", "hinweis"]


def wochenwert(metrik):
    ende = jetzt()
    start = ende - timedelta(days=7)
    try:
        antwort = anfrage(
            "GET", f"{IG_ID}/insights", metric=metrik, period="day", metric_type="total_value",
            since=int(start.timestamp()), until=int(ende.timestamp()),
        )
        return antwort["data"][0]["total_value"]["value"], ""
    except (ApiFehler, KeyError, IndexError) as e:
        return "", f"{metrik}: {e}"


def main():
    profil = anfrage("GET", IG_ID, fields="followers_count,media_count")
    zeile = {"datum": jetzt().date().isoformat(), "follower": profil.get("followers_count", ""), "beitraege": profil.get("media_count", "")}
    hinweise = []
    for spalte, metrik in [("reichweite_7t", "reach"), ("profilaufrufe_7t", "profile_views"), ("interagierende_7t", "accounts_engaged")]:
        zeile[spalte], hinweis = wochenwert(metrik)
        if hinweis:
            hinweise.append(hinweis)
    zeile["hinweis"] = "; ".join(hinweise)
    DATEI.parent.mkdir(exist_ok=True)
    neu = not DATEI.exists()
    with DATEI.open("a", newline="", encoding="utf-8") as f:
        schreiber = csv.DictWriter(f, fieldnames=SPALTEN)
        if neu:
            schreiber.writeheader()
        schreiber.writerow(zeile)
    print(zeile)


if __name__ == "__main__":
    main()
