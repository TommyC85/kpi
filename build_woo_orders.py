#!/usr/bin/env python3
"""Scarica lo storico ordini WooCommerce Varini → woo_varini_orders.json (email → [(data, [corsi])]).
Env: WC_URL / WC_KEY / WC_SECRET."""
import os, requests, certifi, json, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    url = os.environ["WC_URL"].rstrip("/"); k = os.environ["WC_KEY"]; s = os.environ["WC_SECRET"]
    S = requests.Session(); S.verify = certifi.where()
    cust = defaultdict(list); page = 1
    while True:
        for attempt in range(4):
            try:
                r = S.get(f"{url}/wp-json/wc/v3/orders", params={
                    "per_page": 100, "page": page, "status": "completed,processing",
                    "orderby": "date", "order": "asc",
                    "_fields": "date_created,billing,line_items",
                    "consumer_key": k, "consumer_secret": s}, timeout=60)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2)
        d = r.json()
        if not isinstance(d, list) or not d:
            break
        for o in d:
            em = ((o.get("billing", {}) or {}).get("email", "") or "").strip().lower()
            if not em:
                continue
            courses = [it.get("name", "") for it in o.get("line_items", [])]
            cust[em].append((o.get("date_created", ""), courses))
        if len(d) < 100:
            break
        page += 1
    json.dump({e: v for e, v in cust.items()}, open(os.path.join(HERE, "woo_varini_orders.json"), "w"))
    print(f"woo_varini_orders.json: {len(cust)} clienti")


if __name__ == "__main__":
    main()
