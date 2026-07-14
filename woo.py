#!/usr/bin/env python3
"""
Connettore WooCommerce (GuitarTribe) — incasso REALE per settimana.

Ritorna, per un intervallo di date:
  - real_orders / real_revenue     : tutti gli ordini pagati (completed+processing)
  - meta_orders / meta_revenue     : quelli attribuiti a Meta (utm_source fb/ig/facebook/instagram)

Variabili d'ambiente: WC_URL, WC_KEY, WC_SECRET.
"""

import os

import certifi
import requests

META_SOURCES = {"fb", "facebook", "ig", "instagram", "meta"}


def _cfg():
    return (os.environ["WC_URL"].rstrip("/"),
            os.environ["WC_KEY"], os.environ["WC_SECRET"])


def _attr_source(order):
    for m in order.get("meta_data", []):
        if m.get("key") == "_wc_order_attribution_utm_source":
            return (m.get("value") or "").strip().lower()
    return ""


def fetch_week(since_date: str, until_date: str) -> dict:
    """since_date/until_date = 'YYYY-MM-DD' (inclusi)."""
    url, key, secret = _cfg()
    endpoint = f"{url}/wp-json/wc/v3/orders"
    orders, page = [], 1
    while True:
        params = {
            "after": f"{since_date}T00:00:00",
            "before": f"{until_date}T23:59:59",
            "per_page": 100, "page": page,
            "status": "completed,processing",
            "consumer_key": key, "consumer_secret": secret,
        }
        r = requests.get(endpoint, params=params, verify=certifi.where(), timeout=90)
        if r.status_code >= 300:
            raise RuntimeError(f"WooCommerce {r.status_code}: {r.text[:200]}")
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        orders.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    real_rev = sum(float(o.get("total", 0) or 0) for o in orders)
    meta = [o for o in orders if _attr_source(o) in META_SOURCES]
    meta_rev = sum(float(o.get("total", 0) or 0) for o in meta)
    return {
        "real_orders": len(orders),
        "real_revenue": round(real_rev, 2),
        "meta_orders": len(meta),
        "meta_revenue": round(meta_rev, 2),
    }
