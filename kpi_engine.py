#!/usr/bin/env python3
"""
Motore dati della dashboard KPI (scorecard 4 clienti).

Assembla, per la settimana Lun–Dom precedente:
  - Balducci   : persone/gg (evento Acquisto_unico) + CPA + spesa
  - Varini     : profitto reale (incasso Woo − spesa Meta) + ROAS reale
  - Pontoni    : costo/lead + qualità mix + funnel per modulo + trend costo/appuntamento (Odoo)
  - Di Domenico: acquisti + CPA + ROAS front-end

Resiliente: se una fonte (es. Odoo) è irraggiungibile, i suoi campi valgono None
e la dashboard esce comunque con le altre metriche.

Variabili d'ambiente: META_TOKEN (o token passato), WC_*, ODOO_* (opzionali).
"""

import json
import os
from datetime import date, timedelta

import certifi
import requests

from engine import last_week

API = "https://graph.facebook.com/v22.0"
WEEKS_PER_MONTH = 30.4375 / 7  # ≈ 4.348

# ── account & costanti ──────────────────────────────────────────────────────
ACC_BALDUCCI = "act_1083210079422366"
ACC_VARINI = "act_2975289402775458"
ACC_PONTONI = "act_1143079700337559"
ACC_DIDOM = ["act_3097227940528224", "act_1048267528538993"]  # Allin + DDG

# Evento per-persona Balducci (Custom Conversion "Acquisto Unico"); fallback al rollup custom.
BALDUCCI_ACQUISTO_UNICO_ID = "1091386130212380"
DIDOM_BOOK_PRICE = 37.0  # prezzo copertina libro AFS (spedizione inclusa)

PURCHASE_KEYS = ["offsite_conversion.fb_pixel_purchase", "purchase", "omni_purchase"]
LEAD_KEYS = ["lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"]

# Target settimanali (equivalenti mensili tra parentesi nel render)
MONTHLY = {
    "balducci_spend": 20000, "varini_profit": 20000,
    "pontoni_spend": 20000, "didom_spend": 6000, "didom_purchases": 100,
}

# Target ad lanciate/settimana (floor sostenibile ≈ mediana settimane attive, storico 12 sett)
LAUNCH_TARGET = {"balducci": 15, "varini": 20, "pontoni": 10, "didomenico": 20}

# Balducci: CPA purchase su Meta fissata a €9 (media account, valore di riferimento voluto).
BALDUCCI_CPA_DISPLAY = 9.0


def _insights(account, token, since, until, level="account"):
    p = {"access_token": token, "level": level,
         "time_range": json.dumps({"since": since, "until": until}),
         "fields": "spend,actions,action_values", "limit": 500}
    r = requests.get(f"{API}/{account}/insights", params=p, verify=certifi.where(), timeout=90).json()
    if "error" in r:
        raise RuntimeError(f"{account}: {r['error'].get('message')}")
    rows = r.get("data", [])
    if not rows:
        return {"spend": 0.0, "actions": {}}
    d = rows[0]
    return {"spend": float(d.get("spend", 0) or 0),
            "actions": {a["action_type"]: float(a["value"]) for a in d.get("actions", [])}}


def _act(actions, keys):
    for k in keys:
        if k in actions:
            return int(round(actions[k]))
    return 0


def _ads_launched(account, token, since, until):
    """Nr. di ad create nell'intervallo (attività diretta del media buyer)."""
    import datetime as dt
    s = int(dt.datetime.fromisoformat(since + "T00:00:00").timestamp())
    u = int(dt.datetime.fromisoformat(until + "T23:59:59").timestamp())
    filtering = json.dumps([
        {"field": "created_time", "operator": "GREATER_THAN", "value": s},
        {"field": "created_time", "operator": "LESS_THAN", "value": u},
    ])
    p = {"access_token": token, "fields": "id", "filtering": filtering, "limit": 500}
    n, url = 0, f"{API}/{account}/ads"
    while url:
        r = requests.get(url, params=p, verify=certifi.where(), timeout=90).json()
        if "error" in r:
            raise RuntimeError(f"{account} (ads): {r['error'].get('message')}")
        n += len(r.get("data", []))
        url = r.get("paging", {}).get("next")
        p = None
    return n


def _activity(accounts, token, since, until):
    """{launched, active} sommati sugli account (controllabili dal media buyer)."""
    from engine import fetch_active_ads
    if isinstance(accounts, str):
        accounts = [accounts]
    launched = active = 0
    for acc in accounts:
        try:
            launched += _ads_launched(acc, token, since, until)
            active += sum(fetch_active_ads(acc, token).values())
        except Exception:
            pass
    return {"launched": launched, "active": active}


def _month_windows(ref: date, n: int):
    """Le n coorti mensili PIENE precedenti al mese di `ref`. → [(label, since, until)]."""
    first_this = ref.replace(day=1)
    out = []
    m = first_this
    for _ in range(n):
        end = m - timedelta(days=1)          # ultimo giorno del mese precedente
        start = end.replace(day=1)
        out.append((start.strftime("%Y-%m"), start.isoformat(), end.isoformat()))
        m = start
    return list(reversed(out))


# ── clienti ─────────────────────────────────────────────────────────────────
def _balducci(token, since, until):
    ins = _insights(ACC_BALDUCCI, token, since, until)
    spend, acts = ins["spend"], ins["actions"]
    purchases = _act(acts, PURCHASE_KEYS)
    persons = _act(acts, [f"offsite_conversion.custom.{BALDUCCI_ACQUISTO_UNICO_ID}"])
    if not persons:  # conversione appena creata → fallback al rollup evento custom
        persons = _act(acts, ["offsite_conversion.fb_pixel_custom"])
    return {
        "spend": round(spend, 2),
        "purchases": purchases,
        "persons": persons,
        "persons_day": round(persons / 7, 1) if persons else 0,
        "cpa_product": round(spend / purchases, 2) if purchases else None,
        "cpa_display": BALDUCCI_CPA_DISPLAY,  # valore di riferimento fisso €9
        "cpa_person": round(spend / persons, 2) if persons else None,
    }


def _varini(token, since, until):
    ins = _insights(ACC_VARINI, token, since, until)
    spend = ins["spend"]
    out = {"spend": round(spend, 2), "revenue": None, "orders": None,
           "meta_orders": None, "meta_purchases": _act(ins["actions"], PURCHASE_KEYS),
           "profit": None, "roas": None}
    try:
        import woo
        w = woo.fetch_week(since, until)
        rev = w["real_revenue"]
        out.update({"revenue": round(rev, 2), "orders": w["real_orders"],
                    "meta_orders": w["meta_orders"],
                    "profit": round(rev - spend, 2),
                    "roas": round(rev / spend, 2) if spend else None})
    except Exception as e:
        out["error"] = str(e)[:120]
    return out


def _didomenico(token, since, until):
    spend = purchases = 0
    for acc in ACC_DIDOM:
        ins = _insights(acc, token, since, until)
        spend += ins["spend"]
        purchases += _act(ins["actions"], PURCHASE_KEYS)
    revenue = purchases * DIDOM_BOOK_PRICE
    return {
        "spend": round(spend, 2), "purchases": purchases,
        "cpa": round(spend / purchases, 2) if purchases else None,
        "roas": round(revenue / spend, 2) if spend else None,
        "book_price": DIDOM_BOOK_PRICE,
    }


def _pontoni(token, since, until, ref):
    ins = _insights(ACC_PONTONI, token, since, until)
    spend, acts = ins["spend"], ins["actions"]
    leads = _act(acts, LEAD_KEYS)
    out = {
        "spend": round(spend, 2), "leads": leads,
        "cpl": round(spend / leads, 2) if leads else None,
        "spend_month": round(spend * WEEKS_PER_MONTH, 0),
        "quality_pct": None, "types": None, "trend": None, "odoo_error": None,
    }
    # Odoo (sola lettura) — funnel qualità + trend costo/appuntamento
    try:
        import odoo
        cs = (ref - timedelta(days=90)).isoformat()
        cu = (ref - timedelta(days=15)).isoformat()
        types = odoo.funnel_by_type(cs, cu)
        out["types"] = types
        total = sum(t["lead"] for t in types.values())
        high = sum(t["lead"] for n, t in types.items() if n in ("Landing", "Qualificati"))
        out["quality_pct"] = round(100 * high / total) if total else None
        # trend: appuntamenti per mese (Odoo) ÷ spesa Meta per mese
        months = _month_windows(ref, 5)
        appt = odoo.appointments_by_month(months)
        trend = []
        for i, (label, s, u) in enumerate(months):
            a = appt.get(label, {}).get("appt", 0)
            msp = _insights(ACC_PONTONI, token, s, u)["spend"]
            cpa = round(msp / a) if a else None
            immature = (i == len(months) - 1)  # ultimo mese ancora in maturazione
            trend.append({"label": label, "cpa": cpa, "appt": a, "immature": immature})
        out["trend"] = trend
    except Exception as e:
        out["odoo_error"] = str(e)[:160]
    return out


def build_kpi(ref: date, token: str) -> dict:
    start, end = last_week(ref)
    since, until = start.isoformat(), end.isoformat()
    b = _balducci(token, since, until)
    v = _varini(token, since, until)
    p = _pontoni(token, since, until, ref)
    d = _didomenico(token, since, until)
    # KPI di controllo (attività diretta del media buyer): ad lanciate + attive
    b["activity"] = {**_activity(ACC_BALDUCCI, token, since, until), "target": LAUNCH_TARGET["balducci"]}
    v["activity"] = {**_activity(ACC_VARINI, token, since, until), "target": LAUNCH_TARGET["varini"]}
    p["activity"] = {**_activity(ACC_PONTONI, token, since, until), "target": LAUNCH_TARGET["pontoni"]}
    d["activity"] = {**_activity(ACC_DIDOM, token, since, until), "target": LAUNCH_TARGET["didomenico"]}
    return {
        "week_start": since, "week_end": until, "generated_at": None,
        "targets": MONTHLY, "weeks_per_month": WEEKS_PER_MONTH,
        "balducci": b, "varini": v, "pontoni": p, "didomenico": d,
    }


if __name__ == "__main__":
    import sys
    token = os.environ.get("META_TOKEN")
    if not token:
        from store import get_meta_token
        token = get_meta_token()
    ref = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(json.dumps(build_kpi(ref, token), ensure_ascii=False, indent=2))
