#!/usr/bin/env python3
"""
Connettore Google Ads — via foglio Google, non via API.

Non serve developer token né progetto Google Cloud: uno script dentro Google Ads
scrive un foglio ogni ora (_Sistema/google-ads/) e un webhook Apps Script lo
espone come JSON.

Un solo foglio e un solo webhook servono più clienti, una coppia di tab ciascuno:

    pontoni → tab "dati"          (default, retrocompatibile)
    varini  → tab "dati_varini"

Env (una coppia sola, condivisa): GADS_PONTONI_URL, GADS_PONTONI_TOKEN.
Il nome resta quello storico perché i secret esistono già su GitHub con quel nome;
GADS_URL/GADS_TOKEN o GADS_<CLIENTE>_URL/TOKEN hanno la precedenza se presenti,
per il giorno in cui un cliente dovesse avere foglio proprio.

⚠️ LIMITE DI ATTRIBUZIONE (Pontoni): `conversions` è il conteggio DICHIARATO da
Google secondo le sue finestre. In Odoo non esiste nessuna campagna Google
(verificato 2026-08-03: 3.771 lead nel trimestre, tutti Meta), quindi il
costo/appuntamento REALE per Google non è calcolabile: quei numeri stanno accanto
a quelli Meta, non si sommano.

Per Varini vale il contrario: il KPI è il profitto su incasso WooCommerce reale,
che è già di tutti i canali. Lì la spesa Google si somma a quella Meta, altrimenti
il profitto risulta gonfiato esattamente della spesa Google.
"""

import datetime
import os
import time
from zoneinfo import ZoneInfo

import certifi
import requests

ROME = ZoneInfo("Europe/Rome")

# Tab del foglio per cliente. "dati" resta il default storico di Pontoni: il
# webhook lo usa anche quando il parametro non arriva, così una chiamata vecchia
# continua a funzionare.
TABS = {
    "pontoni": "dati",
    "varini": "dati_varini",
}


def _env(client: str, suffix: str) -> str:
    """Risolve URL/TOKEN: override per cliente → generico → nome storico Pontoni."""
    for name in (f"GADS_{client.upper()}_{suffix}", f"GADS_{suffix}",
                 f"GADS_PONTONI_{suffix}"):
        v = os.environ.get(name)
        if v:
            return v
    raise KeyError(f"nessun secret per Google Ads {client} ({suffix})")


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


def _fetch(client: str = "pontoni", attempts: int = 3) -> list:
    """Legge la tab del cliente via webhook.

    Con retry perché il /exec di Apps Script fa un 302 verso googleusercontent e
    quel redirect ogni tanto risponde 404: è transitorio, al giro dopo passa.
    """
    client = client.lower()
    if client not in TABS:
        raise ValueError(f"cliente Google Ads sconosciuto: {client}")
    # Il foglio contiene già tutto lo storico: una lettura per cliente basta,
    # altrimenti la serie a 8 settimane farebbe 8 chiamate identiche.
    if client in _CACHE:
        return _CACHE[client]

    tab = TABS[client]
    url = _env(client, "URL")
    token = _env(client, "TOKEN")
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, params={"token": token, "tab": tab},
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
            # Il webhook a tab fissa ignora il parametro e restituisce SEMPRE la
            # tab di Pontoni. Senza questo controllo la spesa di Pontoni finirebbe
            # nel profitto di Varini senza un solo messaggio d'errore.
            #
            # Il vecchio deployment non rimanda il campo "tab": per "dati" va bene
            # lo stesso (è esattamente ciò che serviva), quindi Pontoni continua a
            # funzionare anche se il webhook non è ancora stato aggiornato. Così
            # l'ordine fra push del codice e ridistribuzione non conta.
            served = data.get("tab")
            if served is None and tab == "dati":
                served = tab
            if served != tab:
                raise RuntimeError(
                    f"webhook: chiesta tab '{tab}', ricevuta '{served or 'nessuna'}'. "
                    "Il deployment Apps Script non è aggiornato: ridistribuisci "
                    "webhook_multi_cliente.js come NUOVA VERSIONE.")
            _CACHE[client] = data.get("rows") or []
            return _CACHE[client]
        except RuntimeError as e:
            if "webhook:" in str(e):
                raise
            last = e
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"webhook non raggiungibile dopo {attempts} tentativi: {last}")


def fetch_week(since_date: str, until_date: str, client: str = "pontoni") -> dict:
    """Spesa e conversioni Google nell'intervallo (date incluse, ora di Roma)."""
    since = datetime.date.fromisoformat(since_date)
    until = datetime.date.fromisoformat(until_date)
    rows = [x for x in _fetch(client) if since <= _day(x["data"]) <= until]

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
    cli = a[2] if len(a) > 2 else "pontoni"
    print(json.dumps(fetch_week(a[0], a[1], cli), indent=2, ensure_ascii=False))
