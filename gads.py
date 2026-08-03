#!/usr/bin/env python3
"""
Connettore Google Ads (Pontoni) — via foglio Google, non via API.

Non serve developer token né progetto Google Cloud: uno script dentro Google Ads
scrive un foglio ogni ora (_Sistema/google-ads-pontoni/gads_to_sheet.js) e un
webhook Apps Script lo espone come JSON.

Env: GADS_PONTONI_URL, GADS_PONTONI_TOKEN.

⚠️ LIMITE DI ATTRIBUZIONE: `conversions` è il conteggio DICHIARATO da Google
secondo le sue finestre. In Odoo non esiste nessuna campagna Google (verificato
2026-08-03: 3.771 lead nel trimestre, tutti Meta), quindi il costo/appuntamento
REALE per Google non è calcolabile: questi numeri stanno accanto a quelli Meta,
non si sommano.
"""

import datetime
import os
import time
from zoneinfo import ZoneInfo

import certifi
import requests

ROME = ZoneInfo("Europe/Rome")


def _day(value) -> datetime.date:
    """Normalizza la colonna data del foglio a una data civile italiana.

    Apps Script serializza le celle-data come ISO UTC ("2026-05-04T22:00:00.000Z"):
    22:00Z è mezzanotte a Roma del 5 maggio, quindi tagliare i primi 10 caratteri
    sposterebbe TUTTO indietro di un giorno. Va convertito, non troncato.
    """
    s = str(value)
    if "T" in s:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(ROME).date()
    return datetime.date.fromisoformat(s[:10])


_CACHE = {}


def _fetch(attempts: int = 3) -> list:
    """Legge il foglio via webhook.

    Con retry perché il /exec di Apps Script fa un 302 verso googleusercontent e
    quel redirect ogni tanto risponde 404: è transitorio, al giro dopo passa.
    """
    # Il foglio contiene già tutto lo storico: una lettura per processo basta,
    # altrimenti la serie a 8 settimane farebbe 8 chiamate identiche.
    if "rows" in _CACHE:
        return _CACHE["rows"]
    url = os.environ["GADS_PONTONI_URL"]
    token = os.environ["GADS_PONTONI_TOKEN"]
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, params={"token": token},
                             verify=certifi.where(), timeout=60)
            if r.status_code >= 300:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
            try:
                data = r.json()
            except ValueError:
                # Apps Script risponde HTML se il deployment è rotto o non autorizzato.
                raise RuntimeError(f"risposta non JSON: {r.text[:120]}")
            if "error" in data:
                # Errore applicativo (token, foglio, tab): inutile ritentare.
                raise RuntimeError(f"webhook: {data['error']}")
            _CACHE["rows"] = data.get("rows") or []
            return _CACHE["rows"]
        except RuntimeError as e:
            if "webhook:" in str(e):
                raise
            last = e
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"webhook non raggiungibile dopo {attempts} tentativi: {last}")


def fetch_week(since_date: str, until_date: str) -> dict:
    """Spesa e conversioni Google nell'intervallo (date incluse, ora di Roma)."""
    since = datetime.date.fromisoformat(since_date)
    until = datetime.date.fromisoformat(until_date)
    rows = [x for x in _fetch() if since <= _day(x["data"]) <= until]

    spend = sum(float(x.get("costo_eur") or 0) for x in rows)
    conv = sum(float(x.get("conversioni") or 0) for x in rows)
    clicks = sum(int(x.get("clic") or 0) for x in rows)
    campaigns = sorted({str(x.get("campagna")) for x in rows})
    return {
        "spend": round(spend, 2),
        "conversions": round(conv, 1),
        "clicks": clicks,
        "cost_per_conversion": round(spend / conv, 2) if conv else None,
        "cpc": round(spend / clicks, 2) if clicks else None,
        "campaigns": campaigns,
        "days": len({_day(x["data"]) for x in rows}),
    }


if __name__ == "__main__":
    import json
    import sys
    a = sys.argv[1:]
    print(json.dumps(fetch_week(a[0], a[1]), indent=2, ensure_ascii=False))
