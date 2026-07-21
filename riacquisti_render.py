#!/usr/bin/env python3
"""Pagina 'Varini · Riacquisti': dopo quanto arriva il 2° acquisto e da quale corso di partenza.
Legge woo_varini_orders.json. Genera riacquisti/index.html (+ .htaccess)."""
import json, os, re, statistics
from collections import defaultdict, Counter
from datetime import datetime

import navbar

HERE = os.path.dirname(os.path.abspath(__file__))


def _clean(n):
    return re.sub(r"\s+", " ", re.sub(r"\[.*?\]|\(.*?\)", "", n or "")).strip()


import courses


def _real(cs):
    return [c for c in cs if not courses.is_excluded(c)]


def canon(name):
    return courses.canon(name)


CSS = """
:root{--bg:#f4f5f7;--panel:#fff;--panel-2:#fbfcfd;--ink:#141a22;--ink-2:#4a5563;--ink-3:#7b8698;--line:#e3e7ec;--line-2:#eef1f4;--accent:#2b57d6;--accent-soft:#e7edfd;--mono:ui-monospace,"SF Mono",Menlo,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;--shadow:0 1px 2px rgba(20,26,34,.05),0 6px 20px rgba(20,26,34,.05)}
@media(prefers-color-scheme:dark){:root{--bg:#0d1017;--panel:#151a22;--panel-2:#11161d;--ink:#e9edf3;--ink-2:#a7b1c0;--ink-3:#6d7788;--line:#242c37;--line-2:#1b222b;--accent:#6f92f5;--accent-soft:#1b2740;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35)}}
:root[data-theme=light]{--bg:#f4f5f7;--panel:#fff;--panel-2:#fbfcfd;--ink:#141a22;--ink-2:#4a5563;--ink-3:#7b8698;--line:#e3e7ec;--line-2:#eef1f4;--accent:#2b57d6;--accent-soft:#e7edfd}
:root[data-theme=dark]{--bg:#0d1017;--panel:#151a22;--panel-2:#11161d;--ink:#e9edf3;--ink-2:#a7b1c0;--ink-3:#6d7788;--line:#242c37;--line-2:#1b222b;--accent:#6f92f5;--accent-soft:#1b2740}
*{box-sizing:border-box}body{margin:0}
.wrap{font-family:var(--sans);background:var(--bg);color:var(--ink);padding:36px 20px 80px;min-height:100vh;-webkit-font-smoothing:antialiased}
.inner{max-width:960px;margin:0 auto}
.head{border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:22px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;align-items:flex-end}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
h1{font-size:clamp(23px,3.5vw,32px);margin:6px 0 2px;letter-spacing:-.02em;font-weight:750}
.sub{color:var(--ink-2);font-size:14px;margin:0}
.upd{font-size:11px;color:var(--ink-3);font-family:var(--mono);display:flex;align-items:center;gap:8px}
.upd button{font-family:var(--sans);font-size:11px;font-weight:600;padding:4px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--accent);cursor:pointer}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:0 0 26px}
@media(max-width:620px){.tiles{grid-template-columns:1fr}}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow)}
.tile .lab{font-size:11.5px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.tile .big{font-family:var(--mono);font-size:30px;font-weight:600;letter-spacing:-.02em;margin-top:8px;line-height:1}
.tile .cap{font-size:12px;color:var(--ink-2);margin-top:6px}
.sec{font-size:17px;font-weight:700;margin:26px 0 4px}
.secsub{color:var(--ink-2);font-size:13px;margin:0 0 14px}
.bar{display:grid;grid-template-columns:92px 1fr 54px;align-items:center;gap:10px;margin:7px 0;font-size:12.5px}
.bar .bl{color:var(--ink-2)}
.track{height:15px;background:var(--line-2);border-radius:7px;overflow:hidden}.fill{height:100%;border-radius:7px;background:var(--accent)}
.bar .pc{text-align:right;font-family:var(--mono);font-weight:600}
.tablewrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;min-width:560px}
thead th{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:700;padding:11px 14px;text-align:right;border-bottom:1px solid var(--line);background:var(--panel-2)}
thead th.l{text-align:left}
tbody td{padding:10px 14px;text-align:right;font-family:var(--mono);font-size:14px;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--line-2)}
tbody td.l{text-align:left;font-family:var(--sans);font-weight:600}
tbody td.nx{text-align:left;font-family:var(--sans);font-size:12.5px;color:var(--ink-2)}
tbody tr:hover{background:var(--panel-2)}
.foot{margin-top:22px;font-size:12px;color:var(--ink-3);line-height:1.6}.foot b{color:var(--ink-2)}
""" + navbar.NAV_CSS


def build():
    raw = json.load(open(os.path.join(HERE, "woo_varini_orders.json")))
    cust = {}
    for em, orders in raw.items():
        parsed = []
        for dt, courses in orders:
            real = _real(courses)          # tiene solo i CORSI VERI (no Community/prova)
            if not real:
                continue                   # ordine di solo prodotti-ponte → ignorato
            try:
                parsed.append((datetime.fromisoformat(dt), real))
            except Exception:
                pass
        if parsed:
            parsed.sort(key=lambda x: x[0])
            cust[em] = parsed

    tot = len(cust)
    gaps = []; fc_all = Counter(); fc_re = Counter(); nxt = defaultdict(Counter); multi = 0
    for em, orders in cust.items():
        entry = canon(orders[0][1][0]) if orders[0][1] else "?"
        fc_all[entry] += 1
        if len(orders) >= 2:
            multi += 1
            gaps.append((orders[1][0] - orders[0][0]).days)
            fc_re[entry] += 1
            for c in orders[1][1]:
                nxt[entry][canon(c)] += 1

    def num(n):
        return f"{n:,}".replace(",", ".")

    med = statistics.median(gaps) if gaps else 0
    buck = Counter()
    for x in gaps:
        b = "≤ 7 giorni" if x <= 7 else "8–30 giorni" if x <= 30 else "1–3 mesi" if x <= 90 else "3–6 mesi" if x <= 180 else "6–12 mesi" if x <= 365 else "> 12 mesi"
        buck[b] += 1
    order = ["≤ 7 giorni", "8–30 giorni", "1–3 mesi", "3–6 mesi", "6–12 mesi", "> 12 mesi"]
    mx = max(buck.values()) if buck else 1
    bars = ""
    for b in order:
        v = buck.get(b, 0)
        bars += (f'<div class="bar"><span class="bl">{b}</span>'
                 f'<span class="track"><span class="fill" style="width:{100*v/mx:.0f}%"></span></span>'
                 f'<span class="pc">{num(v)}</span></div>')

    rows = ""
    for c in sorted((c for c in fc_all if fc_all[c] >= 40), key=lambda x: -fc_re[x] / fc_all[x]):
        n, rp = fc_all[c], fc_re[c]
        top2 = " · ".join(k for k, _ in nxt[c].most_common(2))
        rows += (f'<tr><td class="l">{c}</td><td>{num(n)}</td><td>{100*rp/n:.0f}%</td>'
                 f'<td class="nx">{top2}</td></tr>')

    gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    body = f"""<div class="wrap"><div class="inner">
{navbar.nav_html("/tommaso/kpi/riacquisti/")}
<div class="head">
  <div><div class="eyebrow">Varini · GuitarTribe</div><h1>Riacquisti</h1>
    <p class="sub">Dopo quanto arriva il 2° acquisto e da quale corso di partenza. Fonte: ordini WooCommerce.</p></div>
  <div class="upd">Aggiornato: {gen} <button onclick="location.href=location.pathname+'?_='+Date.now()">🔄 Aggiorna</button></div>
</div>
<div class="tiles">
  <div class="tile"><div class="lab">Clienti totali</div><div class="big">{num(tot)}</div><div class="cap">con almeno un ordine</div></div>
  <div class="tile"><div class="lab">Riacquistano (2+ ordini)</div><div class="big">{num(multi)}</div><div class="cap">{100*multi/tot:.0f}% del totale</div></div>
  <div class="tile"><div class="lab">Tempo al 2° acquisto</div><div class="big">{med:.0f} gg</div><div class="cap">mediana (media {statistics.mean(gaps):.0f} gg)</div></div>
</div>
<div class="sec">Dopo quanto arriva il riacquisto</div>
<p class="secsub">Distribuzione del tempo tra 1° e 2° acquisto. Doppio picco = subito (bundle) + riattivazione a lungo termine.</p>
<div style="max-width:560px">{bars}</div>
<div class="sec">Riacquisto per corso di partenza</div>
<p class="secsub">Dal corso del primo ordine: quanti riacquistano e cosa comprano poi. Ordinato per tasso di riacquisto (min 40 clienti).</p>
<div class="tablewrap"><table>
<thead><tr><th class="l">Corso di partenza</th><th>Clienti</th><th>% riacquista</th><th class="nx">Poi compra</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="foot"><b>Fonte:</b> WooCommerce (ordini completed+processing, sola lettura). Solo <b>corsi veri</b>: esclusi "Iscrizione Nuova Community" (prodotto-ponte migrazione da massimovarini.it, base già esistente) e "Try Before Buy" (prova gratuita). "Corso di partenza" = primo corso vero acquistato. Aggiornato settimanalmente.</div>
</div></div>"""
    return ("<!doctype html>\n<html lang=it>\n<head>\n<meta charset=utf-8>\n"
            "<meta name=viewport content=\"width=device-width, initial-scale=1\">\n"
            "<title>Varini · Riacquisti</title>\n<style>" + CSS + "</style>\n</head>\n<body>\n"
            + body + "\n</body>\n</html>\n")


if __name__ == "__main__":
    out = os.path.join(HERE, "riacquisti")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(build())
    open(os.path.join(out, ".htaccess"), "w", encoding="utf-8").write("DirectoryIndex index.html\nAddDefaultCharset UTF-8\n")
    print("riacquisti/index.html generato")
