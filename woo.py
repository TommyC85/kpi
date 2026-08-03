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

    def gross(o):
        return float(o.get("total", 0) or 0)

    def tax(o):
        """IVA registrata sull'ordine.

        ⚠️ Vale solo per i negozi che calcolano l'imposta. Varini ha due aliquote
        configurate (22% standard, 4% editoria) e prezzi IVA inclusa, quindi
        `total_tax` riflette già il mix per prodotto: non va ricalcolato a mano.
        Balducci e Di Domenico NON hanno aliquote configurate → total_tax = 0 e
        il netto coincide col lordo (l'IVA non è scorporabile dai loro dati).
        """
        return float(o.get("total_tax", 0) or 0)

    real_rev = sum(gross(o) for o in orders)
    real_tax = sum(tax(o) for o in orders)
    customers = {email(o) for o in orders if email(o)}
    meta = [o for o in orders if _is_meta(_attr_source(o))]
    meta_cust = {email(o) for o in meta if email(o)}
    meta_rev = sum(gross(o) for o in meta)
    meta_tax = sum(tax(o) for o in meta)
    return {
        "real_orders": len(orders),
        "real_revenue": round(real_rev, 2),
        "real_revenue_net": round(real_rev - real_tax, 2),
        "real_tax": round(real_tax, 2),
        "real_customers": len(customers),
        "meta_orders": len(meta),
        "meta_revenue": round(meta_rev, 2),
        "meta_revenue_net": round(meta_rev - meta_tax, 2),
        "meta_tax": round(meta_tax, 2),
        "meta_customers": len(meta_cust),
    }
