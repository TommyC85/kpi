#!/usr/bin/env python3
"""Orchestratore 'Spaccato moduli Pontoni' → pontoni/index.html (+ .htaccess).
Dati freschi da Odoo+Meta, poi render interattivo. Deploy su /tommaso/kpi/pontoni/.
Env: ODOO_*, SUPABASE_* (token Meta) o META_TOKEN."""
import os
import sys
from datetime import date

from pontoni_data import build_data
from pontoni_render import build

OUT_DIR = os.path.join(os.path.dirname(__file__), "pontoni")


def _token():
    try:
        from store import get_meta_token
        t = get_meta_token()
        if t:
            print("Token Meta da: Supabase (OAuth)"); return t
    except Exception as e:
        print(f"(avviso) token Supabase fallito: {e}")
    t = os.environ.get("META_TOKEN")
    if not t:
        sys.exit("Nessun token Meta disponibile.")
    print("Token Meta da: env META_TOKEN"); return t


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ref = date.fromisoformat(args[0]) if args else date.today()
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        data = build_data(_token(), ref)
        html = build(data)
        with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(OUT_DIR, ".htaccess"), "w", encoding="utf-8") as f:
            f.write("DirectoryIndex index.html\nAddDefaultCharset UTF-8\n")
        print(f"pontoni/index.html generato · {len(data['modules'])} moduli · aggiornato {data['generated']}")
    except Exception as e:
        # RESILIENZA: fonte giù (es. Odoo throttle) → NON fallire il job e NON toccare
        # la pagina live. Non genero index.html; il deploy salta Pontoni se il file manca.
        print(f"(ERRORE) build Pontoni fallito, salto il deploy Pontoni: {e}")


if __name__ == "__main__":
    main()
