#!/usr/bin/env python3
"""
Orchestratore della dashboard KPI (scorecard 4 clienti).

Ogni lunedì (via GitHub Actions), DOPO run.py:
  1. costruisce il modello KPI della settimana precedente (kpi_engine)
  2. genera kpi/index.html (kpi_render)

Il file viene poi caricato dal workflow in /tommaso/kpi/ su SiteGround.

Env: SUPABASE_URL/KEY (token Meta via OAuth) oppure META_TOKEN; WC_*, ODOO_* opzionali.

Uso:
    python3 kpi_run.py                # settimana precedente a oggi
    python3 kpi_run.py 2026-07-07     # settimana precedente alla data indicata
"""

import os
import sys
from datetime import date, datetime, timezone

from kpi_engine import build_kpi, build_weekly_series
from kpi_render import render_kpi_multiweek

OUT_DIR = os.path.join(os.path.dirname(__file__), "kpi")
OUT = os.path.join(OUT_DIR, "index.html")

HTACCESS = """# /tommaso/kpi — eredita la Basic Auth dalla cartella padre /tommaso.
DirectoryIndex index.html
AddDefaultCharset UTF-8

<IfModule mod_headers.c>
  Header set Cache-Control "no-store, no-cache, must-revalidate, private"
  Header set X-Cache-Enabled "False"
</IfModule>
"""

DOC = ('<!doctype html>\n<html lang="it">\n<head>\n'
       '<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
       '<title>KPI Media Buying — 4 clienti</title>\n'
       '</head>\n<body>\n{body}\n</body>\n</html>\n')


def _token():
    try:
        from store import get_meta_token
        t = get_meta_token()
        if t:
            print("Token Meta da: Supabase (OAuth)")
            return t
    except Exception as e:
        print(f"(avviso) token da Supabase fallito: {e}")
    t = os.environ.get("META_TOKEN")
    if t:
        print("Token Meta da: env META_TOKEN")
        return t
    sys.exit("Nessun token Meta disponibile.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ref = date.fromisoformat(args[0]) if args else date.today()
    token = _token()

    model = build_kpi(ref, token)
    model["generated_at"] = datetime.now(timezone.utc).isoformat()

    p = model["pontoni"]
    if p.get("odoo_error"):
        print(f"(avviso) Odoo non disponibile: {p['odoo_error']}")
    else:
        print(f"Odoo OK · quality_mix={p.get('quality_pct')}% · trend {len(p.get('trend') or [])} mesi")

    series = build_weekly_series(ref, token, n=8)
    print(f"Serie settimanale: {series['weeks'][0]} → {series['weeks'][-1]}")
    html = DOC.format(body=render_kpi_multiweek(model, series))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(OUT_DIR, ".htaccess"), "w", encoding="utf-8") as f:
        f.write(HTACCESS)
    print(f"kpi/index.html generato ({len(html)} byte) · settimana "
          f"{model['week_start']} → {model['week_end']}")


if __name__ == "__main__":
    main()
