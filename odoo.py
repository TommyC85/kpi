#!/usr/bin/env python3
"""
Connettore Odoo (Pontoni) — SOLA LETTURA.

Usa esclusivamente metodi di lettura dell'API esterna XML-RPC
(`search_count`, `read_group`) — nessun create/write/unlink: è read-only
per costruzione, non solo per permessi.

Fornisce, per il funnel commerciale di Pontoni:
  - funnel_by_type(since, until)   : tasso lead→appuntamento per tipo di modulo
                                     (Landing / Lead ADS / Qualificati) — leva qualità
  - quality_mix(since, until)      : % di lead da campagne ad alta conversione
  - appointments_by_month(months)  : nr. appuntamenti per coorte mensile (per il trend)

Variabili d'ambiente: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY.
Se mancano, le funzioni sollevano RuntimeError: il chiamante deve gestirlo
(la dashboard resta viva anche senza Odoo).
"""

import os
import ssl
import xmlrpc.client

import certifi

# Filtro campagne: solo quelle a pagamento gestite da noi.
CAMPAIGN_FILTER = "[TMC]"

# Fasi crm.lead che implicano un appuntamento fissato (a valle del semplice lead).
# La `sequence` di Odoo NON riflette l'ordine reale del funnel → si classifica per nome.
APPT_STAGES = {
    "No Show", "Offerta Si", "Offerta No", "Fissa appuntamento Front",
    "Trattative da chiudere Audiopro", "Visita < 7gg", "Visite < 45gg",
    "ASL in corso", "Prova in corso", "Won",
    "Consegnato da saldare (WIP🛠️)", "Saldato (WIP🛠️)",
}
WON_STAGES = {"Won", "Consegnato da saldare (WIP🛠️)", "Saldato (WIP🛠️)"}


_CLIENT = None  # cache: una sola authenticate per processo (evita il throttle login di Odoo)


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
        raise RuntimeError("Odoo: authenticate fallita (db/utente/chiave o login temporaneamente in throttle).")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=ctx)
    _CLIENT = (models, db, uid, key)
    return _CLIENT


def _read_group(models, db, uid, key, domain, groupby):
    return models.execute_kw(db, uid, key, "crm.lead", "read_group",
                             [domain, [], groupby], {"lazy": False})


def _campaign_type(name: str) -> str:
    n = (name or "").lower()
    if "qualif" in n:
        return "Qualificati"
    if "landing" in n:
        return "Landing"
    return "Lead ADS"


def funnel_by_type(since: str, until: str) -> dict:
    """Coorte matura → {tipo: {lead, appt, rate}}. `since`/`until` = 'YYYY-MM-DD'."""
    models, db, uid, key = _client()
    dom = [["create_date", ">=", since], ["create_date", "<", until],
           ["campaign_id.name", "ilike", CAMPAIGN_FILTER]]
    rows = _read_group(models, db, uid, key, dom, ["campaign_id", "stage_id"])
    out = {}
    for r in rows:
        camp = (r["campaign_id"] or [0, ""])[1]
        st = (r["stage_id"] or [0, "?"])[1]
        c = r.get("__count", 0)
        t = out.setdefault(_campaign_type(camp), {"lead": 0, "appt": 0})
        t["lead"] += c
        if st in APPT_STAGES:
            t["appt"] += c
    for t in out.values():
        t["rate"] = round(100 * t["appt"] / t["lead"], 1) if t["lead"] else 0.0
    return out


def quality_mix(since: str, until: str) -> dict:
    """% di lead da campagne ad alta conversione (Landing + Qualificati) sul totale [TMC]."""
    types = funnel_by_type(since, until)
    total = sum(t["lead"] for t in types.values())
    high = sum(t["lead"] for name, t in types.items() if name in ("Landing", "Qualificati"))
    return {"high": high, "total": total,
            "pct": round(100 * high / total) if total else 0}


def appointments_by_month(months: list) -> dict:
    """months = [(label, since, until), ...] → {label: {'lead':n, 'appt':n}} per coorte."""
    models, db, uid, key = _client()
    out = {}
    for label, since, until in months:
        dom = [["create_date", ">=", since], ["create_date", "<=", until + " 23:59:59"],
               ["campaign_id.name", "ilike", CAMPAIGN_FILTER]]
        rows = _read_group(models, db, uid, key, dom, ["stage_id"])
        lead = sum(r.get("__count", 0) for r in rows)
        appt = sum(r.get("__count", 0) for r in rows if (r["stage_id"] or [0, "?"])[1] in APPT_STAGES)
        out[label] = {"lead": lead, "appt": appt}
    return out


if __name__ == "__main__":
    import json
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=90)).isoformat()
    until = (date.today() - timedelta(days=15)).isoformat()
    print("funnel_by_type:", json.dumps(funnel_by_type(since, until), ensure_ascii=False))
    print("quality_mix:", json.dumps(quality_mix(since, until), ensure_ascii=False))
    months = [("2026-05", "2026-05-01", "2026-05-31"), ("2026-06", "2026-06-01", "2026-06-30")]
    print("appointments_by_month:", json.dumps(appointments_by_month(months), ensure_ascii=False))
