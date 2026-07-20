#!/usr/bin/env python3
"""
Connettore WooCommerce — incasso e ordini REALI per settimana.

Multi-cliente via prefisso variabili:
  - prefix=""          → WC_URL / WC_KEY / WC_SECRET            (Varini/GuitarTribe)
  - prefix="BALDUCCI_" → WC_BALDUCCI_URL / _KEY / _SECRET       (Balducci)

Ritorna, per un intervallo di date (inclusi):
  - real_orders / real_revenue / real_customers   : ordini pagati (completed+processing), clienti unici per email
  - meta_orders / meta_revenue                    : quelli attribuiti a Meta (fb/ig/facebook/instagram, incl. *.facebook.com)
"""

import os

import certifi
import requests


def _is_meta(src: str) -> bool:
    s = (src or "").strip().lower()
    return s in {"fb", "ig", "meta", "instagram", "facebook"} or "facebook" in s or "instagram" in s


def _cfg(prefix=""):
    return (os.environ[f"WC_{prefix}URL"].rstrip("/"),
            os.environ[f"WC_{prefix}KEY"], os.environ[f"WC_{prefix}SECRET"])


def _attr_source(order):
    for m in order.get("meta_data", []):
        if m.get("key") == "_wc_order_attribution_utm_source":
            return (m.get("value") or "").strip().lower()
    return ""


def fetch_week(since_date: str, until_date: str, prefix: str = "") -> dict:
    """since_date/until_date = 'YYYY-MM-DD' (inclusi). prefix per selezionare il cliente."""
    url, key, secret = _cfg(prefix)
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

    def email(o):
        return ((o.get("billing", {}) or {}).get("email", "") or "").strip().lower()

    real_rev = sum(float(o.get("total", 0) or 0) for o in orders)
    customers = {email(o) for o in orders if email(o)}
    meta = [o for o in orders if _is_meta(_attr_source(o))]
    meta_cust = {email(o) for o in meta if email(o)}
    return {
        "real_orders": len(orders),
        "real_revenue": round(real_rev, 2),
        "real_customers": len(customers),
        "meta_orders": len(meta),
        "meta_revenue": round(sum(float(o.get("total", 0) or 0) for o in meta), 2),
        "meta_customers": len(meta_cust),
    }
