#!/usr/bin/env python3
"""
Costruisce i dati dello 'Spaccato moduli Pontoni' (Odoo + Meta).

Per ogni modulo (campagna [TMC]) ATTIVO:
  - lead entrati + appuntamenti fissati per settimana (ultime N settimane)
  - cumulativo dalla creazione del modulo
+ costo per appuntamento per FONTE (Landing / Lead ADS): spesa Meta ÷ appuntamenti.

"Appuntamento fissato" = campo Odoo `x_studio_stato_appuntamento` ∈ (Fissato, No show, Presentato).
Odoo: SOLA LETTURA. Env: ODOO_*, META_TOKEN (o passato).
"""
import json
import os
import ssl
import xmlrpc.client
from datetime import date, datetime, timedelta

import certifi
import requests

ACC_PONTONI = "act_1143079700337559"
BOOKED = {"Fissato", "No show", "Presentato"}
N_WEEKS = 12


def _odoo():
    url = os.environ["ODOO_URL"].rstrip("/"); db = os.environ["ODOO_DB"]
    user = os.environ["ODOO_USER"]; key = os.environ["ODOO_API_KEY"]
    ctx = ssl.create_default_context(cafile=certifi.where())
    uid = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", context=ctx).authenticate(db, user, key, {})
    if not uid:
        raise RuntimeError("Odoo authenticate fallita")
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=ctx), db, uid, key


def _clean(c):
    return c.replace("[ONLINE]", "").replace("[TMC]", "").strip(" |")


def _source(name):
    return "Landing" if "landing" in name.lower() else "Lead ADS"


def _isoweek(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def build_data(token: str, ref: date = None) -> dict:
    ref = ref or date.today()
    M, db, uid, key = _odoo()

    def rg(dom, gb):
        return M.execute_kw(db, uid, key, "crm.lead", "read_group", [dom, [], gb], {"lazy": False})

    monday = ref - timedelta(days=ref.weekday())
    weeks = [_isoweek(monday - timedelta(days=7 * i)) for i in range(N_WEEKS)][::-1]
    since = (monday - timedelta(days=7 * (N_WEEKS - 1))).isoformat()

    # cumulativo per modulo
    CUM = {}
    for r in rg([["campaign_id.name", "ilike", "[TMC]"]], ["campaign_id", "x_studio_stato_appuntamento"]):
        c = (r["campaign_id"] or [0, ""])[1]; st = r.get("x_studio_stato_appuntamento") or "No app"
        d = CUM.setdefault(c, {"lead": 0, "appt": 0}); d["lead"] += r["__count"]
        if st in BOOKED:
            d["appt"] += r["__count"]
    # attivi = lead negli ultimi 14 giorni
    d14 = (ref - timedelta(days=14)).isoformat()
    active = {(r["campaign_id"] or [0, ""])[1] for r in
              rg([["campaign_id.name", "ilike", "[TMC]"], ["create_date", ">=", d14]], ["campaign_id"]) if r["__count"]}
    # settimanale per modulo
    WK = {}
    for r in rg([["campaign_id.name", "ilike", "[TMC]"], ["create_date", ">=", since]],
                ["campaign_id", "create_date:week", "x_studio_stato_appuntamento"]):
        wlabel = r.get("create_date:week")
        if not wlabel:
            continue
        c = (r["campaign_id"] or [0, ""])[1]; st = r.get("x_studio_stato_appuntamento") or "No app"
        ww, yy = wlabel.replace("W", "").split(); iso = f"{yy}-W{int(ww):02d}"
        d = WK.setdefault(c, {}).setdefault(iso, {"lead": 0, "appt": 0}); d["lead"] += r["__count"]
        if st in BOOKED:
            d["appt"] += r["__count"]

    modules = [{"name": _clean(c), "source": _source(c), "cum": d, "weekly": WK.get(c, {})}
               for c, d in CUM.items() if c in active and "?" not in c]
    modules.sort(key=lambda m: -m["cum"]["lead"])

    # Meta spesa per fonte
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

    cum_spend = {"Landing": 0.0, "Lead ADS": 0.0}
    for r in meta("2024-01-01", ref.isoformat()):
        cum_spend[_source(r["campaign_name"])] += float(r.get("spend", 0) or 0)
    wk_spend = {w: {"Landing": 0.0, "Lead ADS": 0.0} for w in weeks}
    for r in meta(since, ref.isoformat(), inc=1):
        iso = _isoweek(datetime.fromisoformat(r["date_start"]).date())
        if iso in wk_spend:
            wk_spend[iso][_source(r["campaign_name"])] += float(r.get("spend", 0) or 0)

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
