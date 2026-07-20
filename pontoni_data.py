#!/usr/bin/env python3
"""
Dati 'Spaccato moduli Pontoni' (Odoo + Meta).

Per ogni modulo (campagna [TMC]) ATTIVO: lead entrati + appuntamenti PRESENTATI
(dominio ufficiale Pontoni, vedi odoo.py) per settimana e cumulativo dalla creazione.
+ costo per appuntamento presentato per FONTE (Landing / Lead ADS).

Odoo: SOLA LETTURA. Env: ODOO_*, META_TOKEN (o passato).
"""
import json
import os
from datetime import date, datetime, timedelta

import certifi
import requests

import odoo  # riuso connessione + dominio ufficiale (PRES_DOMAIN / LEAD_ACTIVE)

ACC_PONTONI = "act_1143079700337559"
N_WEEKS = 12


def _clean(c):
    return c.replace("[ONLINE]", "").replace("[TMC]", "").strip(" |")


def _source(name):
    return "Landing" if "landing" in name.lower() else "Lead ADS"


# Mappa nome campagna Meta → prodotto (deve combaciare col 1° segmento del modulo Odoo).
# Solo corrispondenze 1:1 pulite. I generici lead-gen (Prova/Test/Mese/Quiz/Leads)
# alimentano più moduli → NON mappati (il modulo mostra "n.d." invece di un costo gonfiato).
PROD_KW = [
    ("occhialipersentire", "Occhiali"), ("nuance", "Occhiali"),
    ("apparecchi acustici gratis", "AA Gratis"),
    ("guida al prezzo", "Guida al prezzo"),
    ("phonak lyric", "Lyric"), ("lyric", "Lyric"),
    ("oticon", "Oticon Zeal"), ("padova", "Apertura Padova"),
    ("non bastano", "Gli AA Non Bastano Libro"), ("multi brand", "Multi Brand"),
]


def _meta_key(campaign_name):
    """(prodotto, fonte) da un nome campagna Meta; prodotto None se non mappabile."""
    n = (campaign_name or "").lower()
    prod = next((p for kw, p in PROD_KW if kw in n), None)
    return (prod, _source(campaign_name))


def _isoweek(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _parse_weeks(rows):
    out = {}
    for r in rows:
        c = (r["campaign_id"] or [0, ""])[1]; wl = r.get("create_date:week")
        if not wl:
            continue
        ww, yy = wl.replace("W", "").split()
        out.setdefault(c, {})[f"{yy}-W{int(ww):02d}"] = r["__count"]
    return out


def build_data(token: str, ref: date = None) -> dict:
    ref = ref or date.today()
    monday = ref - timedelta(days=ref.weekday())
    weeks = [_isoweek(monday - timedelta(days=7 * i)) for i in range(N_WEEKS)][::-1]
    since = (monday - timedelta(days=7 * (N_WEEKS - 1))).isoformat()
    camp = [("campaign_id.name", "ilike", odoo.CAMPAIGN_FILTER)]

    # Odoo: cumulativo, attivi, settimanale (lead entrati + presentati)
    cum_lead = odoo._by_campaign(camp + odoo.LEAD_ACTIVE)
    cum_pres = odoo._by_campaign(odoo.PRES_DOMAIN + camp)
    d14 = (ref - timedelta(days=14)).isoformat()
    active = set(odoo._by_campaign(camp + odoo.LEAD_ACTIVE + [("create_date", ">=", d14)]).keys())
    win = [("create_date", ">=", since)]
    wl = _parse_weeks(odoo._rg(camp + odoo.LEAD_ACTIVE + win, ["campaign_id", "create_date:week"]))
    wp = _parse_weeks(odoo._rg(odoo.PRES_DOMAIN + camp + win, ["campaign_id", "create_date:week"]))

    modules = []
    for c, nlead in cum_lead.items():
        if c not in active or "?" in c:
            continue
        weekly = {w: {"lead": wl.get(c, {}).get(w, 0), "appt": wp.get(c, {}).get(w, 0)} for w in weeks}
        modules.append({"name": _clean(c), "source": _source(c),
                        "cum": {"lead": nlead, "appt": cum_pres.get(c, 0)}, "weekly": weekly})
    modules.sort(key=lambda m: -m["cum"]["lead"])

    # Meta: spesa per fonte
    def meta(since_d, until_d, inc=None):
        p = {"access_token": token, "level": "campaign",
             "time_range": json.dumps({"since": since_d, "until": until_d}),
             "fields": "campaign_name,spend", "limit": 500}
        if inc:
            p["time_increment"] = inc
        out, u = [], f"https://graph.facebook.com/v22.0/{ACC_PONTONI}/insights"
        while u:
            r = requests.get(u, params=p, verify=certifi.where(), timeout=90).json()
            if "error" in r:
                break
            out += r.get("data", []); u = r.get("paging", {}).get("next"); p = None
        return out

    from collections import defaultdict
    cum_spend = {"Landing": 0.0, "Lead ADS": 0.0}
    cum_spend_key = defaultdict(float)   # (prodotto, fonte) → spesa (per modulo)
    for r in meta("2024-01-01", ref.isoformat()):
        sp = float(r.get("spend", 0) or 0)
        cum_spend[_source(r["campaign_name"])] += sp
        cum_spend_key[_meta_key(r["campaign_name"])] += sp
    wk_spend = {w: {"Landing": 0.0, "Lead ADS": 0.0} for w in weeks}
    wk_spend_key = {w: defaultdict(float) for w in weeks}
    for r in meta(since, ref.isoformat(), inc=1):
        iso = _isoweek(datetime.fromisoformat(r["date_start"]).date())
        if iso in wk_spend:
            sp = float(r.get("spend", 0) or 0)
            wk_spend[iso][_source(r["campaign_name"])] += sp
            wk_spend_key[iso][_meta_key(r["campaign_name"])] += sp

    # spesa Meta REALE per singolo modulo (prodotto×fonte) → costo/appuntamento per modulo
    for mdl in modules:
        prod = mdl["name"].split("|")[0].strip()
        key = (prod, mdl["source"])
        csp = cum_spend_key.get(key, 0.0)
        mdl["cum"]["spend"] = round(csp)
        mdl["cum"]["cpa"] = round(csp / mdl["cum"]["appt"]) if mdl["cum"]["appt"] else None
        for w in weeks:
            wsp = wk_spend_key.get(w, {}).get(key, 0.0)
            wa = mdl["weekly"][w]["appt"]
            mdl["weekly"][w]["spend"] = round(wsp)
            mdl["weekly"][w]["cpa"] = round(wsp / wa) if wa else None

    def appt_src(weekly=None):
        o = {"Landing": 0, "Lead ADS": 0}
        for m in modules:
            o[m["source"]] += (m["weekly"].get(weekly, {}).get("appt", 0) if weekly else m["cum"]["appt"])
        return o

    ca = appt_src()
    cost = {"cum": {s: {"spend": round(cum_spend[s]), "appt": ca[s],
                        "cpa": round(cum_spend[s] / ca[s]) if ca[s] else None} for s in ("Landing", "Lead ADS")},
            "weekly": {w: {s: {"spend": round(wk_spend[w][s]), "appt": appt_src(w)[s],
                               "cpa": round(wk_spend[w][s] / appt_src(w)[s]) if appt_src(w)[s] else None}
                           for s in ("Landing", "Lead ADS")} for w in weeks}}

    return {"generated": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "weeks": weeks, "modules": modules, "cost_source": cost}
