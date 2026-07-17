#!/usr/bin/env python3
"""
Connettore Odoo (Pontoni) — SOLA LETTURA.

Usa solo metodi di lettura (`search_count`, `read_group`) — nessun create/write/unlink.

"Appuntamento presentato (vendibile)" = dominio ufficiale del tecnico Pontoni:
  type=opportunity, lost_reason_id NOT IN [12],
  calendar_event_ids.esito_appuntamento_ids.presentato = 'presentato',
  active IN [True, False]   (include gli archiviati: vinti/persi)
"Lead entrati" = tutti i crm.lead della campagna con active IN [True, False].

Variabili d'ambiente: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY.
Se mancano, le funzioni sollevano RuntimeError (il chiamante degrada con grazia).
"""

import os
import ssl
import xmlrpc.client

import certifi

CAMPAIGN_FILTER = "[TMC]"

# Dominio ufficiale Pontoni per "presentato ipoacusico" (il vendibile).
PRES_DOMAIN = [
    ("type", "=", "opportunity"),
    ("lost_reason_id", "not in", [12]),
    ("calendar_event_ids.esito_appuntamento_ids.presentato", "=", "presentato"),
    ("active", "in", [True, False]),
]
# Denominatore "lead entrati": tutti i record (anche archiviati).
LEAD_ACTIVE = [("active", "in", [True, False])]

_CLIENT = None  # una sola authenticate per processo (evita il throttle login di Odoo)


def _client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        url = os.environ["ODOO_URL"].rstrip("/")
        db = os.environ["ODOO_DB"]
        user = os.environ["ODOO_USER"]
        key = os.environ["ODOO_API_KEY"]
    except KeyError as e:
        raise RuntimeError(f"Credenziali Odoo mancanti: {e}")
    ctx = ssl.create_default_context(cafile=certifi.where())
    uid = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", context=ctx).authenticate(db, user, key, {})
    if not uid:
        raise RuntimeError("Odoo: authenticate fallita (db/utente/chiave o login in throttle).")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=ctx)
    _CLIENT = (models, db, uid, key)
    return _CLIENT


def _rg(dom, groupby):
    models, db, uid, key = _client()
    return models.execute_kw(db, uid, key, "crm.lead", "read_group", [dom, [], groupby], {"lazy": False})


def _count(dom):
    models, db, uid, key = _client()
    return models.execute_kw(db, uid, key, "crm.lead", "search_count", [dom])


def _campaign_type(name: str) -> str:
    n = (name or "").lower()
    if "qualif" in n:
        return "Qualificati"
    if "landing" in n:
        return "Landing"
    return "Lead ADS"


def _by_campaign(dom):
    return {(r["campaign_id"] or [0, ""])[1]: r["__count"] for r in _rg(dom, ["campaign_id"])}


def funnel_by_campaign(since: str, until: str) -> list:
    """[{campaign, type, lead, appt, rate}] per campagna [TMC], coorte per create_date.
    appt = presentati (dominio ufficiale); lead = record entrati (active T/F)."""
    win = [("create_date", ">=", since), ("create_date", "<", until)]
    camp = [("campaign_id.name", "ilike", CAMPAIGN_FILTER)]
    leads = _by_campaign(camp + LEAD_ACTIVE + win)
    pres = _by_campaign(PRES_DOMAIN + camp + win)
    out = [{"campaign": c, "type": _campaign_type(c), "lead": n, "appt": pres.get(c, 0),
            "rate": round(100 * pres.get(c, 0) / n, 1) if n else 0.0}
           for c, n in leads.items()]
    out.sort(key=lambda x: -x["rate"])
    return out


def funnel_by_type(since: str, until: str) -> dict:
    """{tipo: {lead, appt, rate}} aggregando le campagne."""
    out = {}
    for m in funnel_by_campaign(since, until):
        t = out.setdefault(m["type"], {"lead": 0, "appt": 0})
        t["lead"] += m["lead"]; t["appt"] += m["appt"]
    for t in out.values():
        t["rate"] = round(100 * t["appt"] / t["lead"], 1) if t["lead"] else 0.0
    return out


def quality_mix(since: str, until: str) -> dict:
    types = funnel_by_type(since, until)
    total = sum(t["lead"] for t in types.values())
    high = sum(t["lead"] for n, t in types.items() if n in ("Landing", "Qualificati"))
    return {"high": high, "total": total, "pct": round(100 * high / total) if total else 0}


def appointments_by_month(months: list) -> dict:
    """months=[(label,since,until)] → {label:{'lead':n,'appt':n}} (presentati / entrati)."""
    camp = [("campaign_id.name", "ilike", CAMPAIGN_FILTER)]
    out = {}
    for label, s, u in months:
        win = [("create_date", ">=", s), ("create_date", "<=", u + " 23:59:59")]
        out[label] = {"lead": _count(camp + LEAD_ACTIVE + win),
                      "appt": _count(PRES_DOMAIN + camp + win)}
    return out


if __name__ == "__main__":
    import json
    from datetime import date, timedelta
    s = (date.today() - timedelta(days=90)).isoformat()
    u = (date.today() - timedelta(days=15)).isoformat()
    print("funnel_by_type:", json.dumps(funnel_by_type(s, u), ensure_ascii=False))
    print("quality_mix:", json.dumps(quality_mix(s, u), ensure_ascii=False))
