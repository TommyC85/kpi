#!/usr/bin/env python3
"""
Persistenza dello storico su Supabase (tabella `snapshots`).

Due funzioni:
  - upsert_snapshot(snap): scrive/aggiorna le righe della settimana
  - fetch_history():        rilegge tutto lo storico nella forma-snapshot
                            usata da render.py (lista, dal più vecchio al più recente)
"""

import os

import certifi
import requests

TABLE = "snapshots"


def _cfg():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_KEY"]
    return url, {"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"}


def _rows_from_snapshot(snap):
    rows = []
    common = {"week_start": snap["week_start"], "week_end": snap["week_end"],
              "generated_at": snap.get("generated_at")}
    for p in snap["projects"]:
        rows.append({**common, "project": p["project"], "product": "", "level": "client",
                     "kpi": p["kpi"], "spend": p["spend"], "results": p["results"],
                     "cost_per_result": p["cost_per_result"], "atc": p["atc"],
                     "active_ads": p.get("active_ads"),
                     "real_orders": p.get("real_orders"), "real_revenue": p.get("real_revenue"),
                     "meta_orders": p.get("meta_orders"), "meta_revenue": p.get("meta_revenue")})
        for pr in p["products"]:
            rows.append({**common, "project": p["project"], "product": pr["product"],
                         "level": "product", "kpi": p["kpi"], "spend": pr["spend"],
                         "results": pr["results"], "cost_per_result": pr["cost_per_result"],
                         "atc": pr["atc"], "active_ads": pr.get("active_ads", 0),
                         # stesse chiavi delle righe client (PostgREST lo richiede nel batch)
                         "real_orders": None, "real_revenue": None,
                         "meta_orders": None, "meta_revenue": None})
    return rows


def upsert_snapshot(snap):
    url, headers = _cfg()
    headers = {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    rows = _rows_from_snapshot(snap)
    r = requests.post(f"{url}/rest/v1/{TABLE}", headers=headers, json=rows,
                      verify=certifi.where(), timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase upsert {r.status_code}: {r.text}")
    return len(rows)


def get_meta_token():
    """Legge il token Meta salvato dal flusso OAuth (tabella meta_auth, riga id=1).
    Ritorna None se non c'è ancora un collegamento."""
    url, headers = _cfg()
    r = requests.get(f"{url}/rest/v1/meta_auth",
                     params={"id": "eq.1", "select": "access_token,expires_at"},
                     headers=headers, verify=certifi.where(), timeout=30)
    if r.status_code >= 300:
        return None
    rows = r.json()
    return rows[0]["access_token"] if rows else None


def fetch_history():
    url, headers = _cfg()
    r = requests.get(f"{url}/rest/v1/{TABLE}",
                     params={"select": "*", "order": "week_start.asc"},
                     headers=headers, verify=certifi.where(), timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase fetch {r.status_code}: {r.text}")
    rows = r.json()

    weeks = {}  # week_start → snapshot
    for row in rows:
        ws = row["week_start"]
        wk = weeks.setdefault(ws, {"week_start": ws, "week_end": row["week_end"],
                                   "generated_at": row.get("generated_at"), "_proj": {}})
        proj = wk["_proj"].setdefault(row["project"], {
            "project": row["project"], "kpi": row["kpi"],
            "spend": 0.0, "results": 0, "cost_per_result": None, "atc": 0,
            "active_ads": None, "real_orders": None, "real_revenue": None,
            "meta_orders": None, "meta_revenue": None, "products": []})

        def _f(v):
            return float(v) if v is not None else None

        def _i(v):
            return int(v) if v is not None else None

        if row["level"] == "client":
            proj.update({"spend": float(row["spend"]), "results": int(row["results"]),
                         "cost_per_result": _f(row["cost_per_result"]), "atc": int(row["atc"]),
                         "active_ads": _i(row.get("active_ads")),
                         "real_orders": _i(row.get("real_orders")), "real_revenue": _f(row.get("real_revenue")),
                         "meta_orders": _i(row.get("meta_orders")), "meta_revenue": _f(row.get("meta_revenue"))})
        else:
            proj["products"].append({
                "product": row["product"], "spend": float(row["spend"]),
                "results": int(row["results"]), "cost_per_result": _f(row["cost_per_result"]),
                "atc": int(row["atc"]), "active_ads": int(row.get("active_ads") or 0)})

    history = []
    for ws in sorted(weeks):
        wk = weeks[ws]
        projects = list(wk.pop("_proj").values())
        for p in projects:
            p["products"].sort(key=lambda x: x["spend"], reverse=True)
        wk["projects"] = projects
        history.append(wk)
    return history
