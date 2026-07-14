#!/usr/bin/env python3
"""
Motore dati del Riepilogo Lunedì.

Tira gli insight Meta a livello campagna per ogni progetto configurato,
mappa campagna → prodotto, calcola i KPI (purchase/lead), il costo per
risultato PESATO sulla spesa (spesa totale ÷ risultati totali) a livello
cliente e il dettaglio per prodotto.

Uso stand-alone (test locale):
    META_TOKEN="EAAX..." python3 engine.py [YYYY-MM-DD]
    (data opzionale = un giorno qualsiasi della settimana da riportare;
     default = oggi → riporta la settimana Lun–Dom precedente)
"""

import json
import os
import sys
from datetime import date, timedelta

import certifi
import requests

from config import ACTION_KEYS, PROJECTS

API = "https://graph.facebook.com/v22.0"


# ── periodo ────────────────────────────────────────────────────────────────
def last_week(ref: date):
    """Settimana Lun–Dom precedente rispetto a `ref`."""
    monday_this = ref - timedelta(days=ref.weekday())
    start = monday_this - timedelta(days=7)
    end = monday_this - timedelta(days=1)
    return start, end


# ── parsing prodotto ─────────────────────────────────────────────────────────
def product_from_campaign(name: str, aliases: dict) -> str:
    parts = [p.strip() for p in name.split("|")]
    if parts and parts[0].upper() == "TMC":
        parts = parts[1:]
    prod = parts[0] if parts and parts[0] else name.strip()
    prod = prod.split(" - ")[0].strip()  # toglie la data finale "Prodotto - 26/05"
    return aliases.get(prod.lower(), prod)


def action_value(actions: list, kind: str) -> int:
    """Somma il primo action_type disponibile per `kind` (purchase/lead/atc)."""
    by_type = {a["action_type"]: float(a["value"]) for a in (actions or [])}
    for key in ACTION_KEYS[kind]:
        if key in by_type:
            return int(round(by_type[key]))
    return 0


# ── fetch ─────────────────────────────────────────────────────────────────────
def fetch_campaigns(account: str, token: str, since: str, until: str) -> list:
    params = {
        "access_token": token,
        "level": "campaign",
        "time_range": json.dumps({"since": since, "until": until}),
        "fields": "campaign_name,spend,actions",
        "limit": 500,
    }
    rows, url = [], f"{API}/{account}/insights"
    while url:
        r = requests.get(url, params=params, verify=certifi.where(), timeout=90)
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"{account}: {data['error'].get('message')}")
        rows.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = None  # `next` è già completo di query string
    return rows


def fetch_active_ads(account: str, token: str) -> dict:
    """Conta le ads REALMENTE in erogazione (effective_status ACTIVE = ad accesa
    su adset acceso su campagna accesa), raggruppate per nome campagna."""
    params = {
        "access_token": token,
        "effective_status": json.dumps(["ACTIVE"]),
        "fields": "campaign{name}",
        "limit": 500,
    }
    counts, url = {}, f"{API}/{account}/ads"
    while url:
        r = requests.get(url, params=params, verify=certifi.where(), timeout=90)
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"{account} (ads): {data['error'].get('message')}")
        for ad in data.get("data", []):
            cname = (ad.get("campaign") or {}).get("name", "")
            counts[cname] = counts.get(cname, 0) + 1
        url = data.get("paging", {}).get("next")
        params = None
    return counts


# ── calcolo ─────────────────────────────────────────────────────────────────
def build_snapshot(ref: date, token: str, include_active: bool = True,
                   include_woo: bool = True) -> dict:
    start, end = last_week(ref)
    since, until = start.isoformat(), end.isoformat()
    out_projects = []

    for proj in PROJECTS:
        kpi = proj["kpi"]
        aliases = proj.get("aliases", {})
        exclude = proj.get("exclude", [])
        products = {}  # nome → {spend, results, atc, active_ads}
        p_spend = p_results = p_atc = 0.0
        p_active = 0

        def _slot(name):
            return products.setdefault(name, {"spend": 0.0, "results": 0, "atc": 0, "active_ads": 0})

        for account in proj["accounts"]:
            for row in fetch_campaigns(account, token, since, until):
                cname = row.get("campaign_name", "")
                if any(x.lower() in cname.lower() for x in exclude):
                    continue
                spend = float(row.get("spend", 0) or 0)
                res = action_value(row.get("actions"), kpi)
                atc = action_value(row.get("actions"), "atc")
                if spend == 0 and res == 0:
                    continue
                d = _slot(product_from_campaign(cname, aliases))
                d["spend"] += spend
                d["results"] += res
                d["atc"] += atc
                p_spend += spend
                p_results += res
                p_atc += atc

            # ads attive (stato attuale) — solo per la settimana corrente
            if include_active:
                for cname, c in fetch_active_ads(account, token).items():
                    if any(x.lower() in cname.lower() for x in exclude):
                        continue
                    _slot(product_from_campaign(cname, aliases))["active_ads"] += c
                    p_active += c

        def cpr(spend, results):
            return round(spend / results, 2) if results else None

        prod_list = sorted(
            (
                {
                    "product": name,
                    "spend": round(v["spend"], 2),
                    "results": v["results"],
                    "cost_per_result": cpr(v["spend"], v["results"]),
                    "atc": v["atc"],
                    "active_ads": v["active_ads"],
                }
                for name, v in products.items()
            ),
            key=lambda x: x["spend"],
            reverse=True,
        )

        entry = {
            "project": proj["name"],
            "kpi": kpi,
            "spend": round(p_spend, 2),
            "results": int(p_results),
            "cost_per_result": cpr(p_spend, p_results),
            "atc": int(p_atc),
            "active_ads": int(p_active) if include_active else None,
            "products": prod_list,
        }

        # Incasso reale (WooCommerce) per i progetti che ce l'hanno
        if include_woo and proj.get("woo"):
            import woo
            w = woo.fetch_week(since, until)
            entry.update({
                "real_orders": w["real_orders"],
                "real_revenue": w["real_revenue"],
                "meta_orders": w["meta_orders"],
                "meta_revenue": w["meta_revenue"],
                "monthly_profit_target": proj.get("monthly_profit_target"),
                "monthly_fixed_costs": proj.get("monthly_fixed_costs", 0),
            })

        out_projects.append(entry)

    return {
        "week_start": since,
        "week_end": until,
        "generated_at": None,  # timbrato da run.py
        "projects": out_projects,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = os.environ.get("META_TOKEN")
    if not token:
        sys.exit("META_TOKEN mancante nell'ambiente.")
    ref = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    snap = build_snapshot(ref, token)
    print(json.dumps(snap, ensure_ascii=False, indent=2))
