#!/usr/bin/env python3
"""Pagina statica 'Varini · Corsi (LearnDash)': quante persone hanno 1 solo corso e quali.
Legge ld_user_courses.json + ld_courses.json. Genera ld/index.html (+ .htaccess)."""
import json
import os
import re
from collections import Counter
from datetime import datetime

import navbar

HERE = os.path.dirname(os.path.abspath(__file__))


def _clean(t):
    t = re.sub(r"&#?\w+;", " ", t or "")
    return re.sub(r"\s+", " ", t).strip()


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
.tablewrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;min-width:420px}
thead th{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:700;padding:11px 14px;text-align:right;border-bottom:1px solid var(--line);background:var(--panel-2)}
thead th.l{text-align:left}
tbody td{padding:10px 14px;text-align:right;font-family:var(--mono);font-size:14px;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--line-2)}
tbody td.l{text-align:left;font-family:var(--sans);font-weight:600}
tbody tr:hover{background:var(--panel-2)}
.bar{display:grid;grid-template-columns:56px 1fr 60px;align-items:center;gap:10px;margin:7px 0;font-size:12.5px}
.bar .bl{color:var(--ink-2);font-family:var(--mono)}
.track{height:15px;background:var(--line-2);border-radius:7px;overflow:hidden}.fill{height:100%;border-radius:7px;background:var(--accent)}
.bar .pc{text-align:right;font-family:var(--mono);font-weight:600}
.foot{margin-top:22px;font-size:12px;color:var(--ink-3);line-height:1.6}.foot b{color:var(--ink-2)}
""" + navbar.NAV_CSS


def build():
    import courses as C
    uc = {int(u): set(cs) for u, cs in json.load(open(os.path.join(HERE, "ld_user_courses.json"))).items()}
    ctitles = {int(k): v for k, v in json.load(open(os.path.join(HERE, "ld_courses.json"))).items()}

    # ogni utente → set di LINEE canoniche (Vol.1/2/3 e sigle → una sola linea; esclusi ponte/prova/bonus)
    def lines_of(cids):
        ls = set()
        for cid in cids:
            t = ctitles.get(cid, str(cid))
            if C.is_excluded(t):
                continue
            ln = C.canon(t)
            if ln in C.EXCLUDE_CANON:
                continue
            ls.add(ln)
        return ls

    user_lines = {u: lines_of(v) for u, v in uc.items()}
    user_lines = {u: ls for u, ls in user_lines.items() if ls}  # almeno 1 linea vera
    total = len(user_lines)
    ncourses = Counter(len(ls) for ls in user_lines.values())
    one = [u for u, ls in user_lines.items() if len(ls) == 1]
    single_by_course = Counter(next(iter(user_lines[u])) for u in one)

    def num(n):
        return f"{n:,}".replace(",", ".")

    # tabella single-linea per corso
    rows = ""
    for line, n in single_by_course.most_common():
        pct = 100 * n / len(one) if one else 0
        rows += (f'<tr><td class="l">{line}</td>'
                 f'<td>{num(n)}</td><td>{pct:.1f}%</td></tr>')

    # distribuzione nr linee/persona (1,2,3,4+)
    b1, b2, b3 = ncourses.get(1, 0), ncourses.get(2, 0), ncourses.get(3, 0)
    b4 = sum(v for k, v in ncourses.items() if k >= 4)
    dist = [("1 corso", b1), ("2 corsi", b2), ("3 corsi", b3), ("4+ corsi", b4)]
    mx = max(v for _, v in dist) or 1
    bars = ""
    for lab, v in dist:
        bars += (f'<div class="bar"><span class="bl">{lab}</span>'
                 f'<span class="track"><span class="fill" style="width:{100*v/mx:.0f}%"></span></span>'
                 f'<span class="pc">{num(v)}</span></div>')

    gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    body = f"""<div class="wrap"><div class="inner">
{navbar.nav_html("/tommaso/kpi/learndash/")}
<div class="head">
  <div><div class="eyebrow">Varini · GuitarTribe</div><h1>Corsi (LearnDash)</h1>
    <p class="sub">Chi possiede i corsi — clienti Woo <b>e migrati dal vecchio portale</b>.</p></div>
  <div class="upd">Aggiornato: {gen} <button onclick="location.href=location.pathname+'?_='+Date.now()">🔄 Aggiorna</button></div>
</div>
<div class="tiles">
  <div class="tile"><div class="lab">Persone con ≥1 corso</div><div class="big">{num(total)}</div><div class="cap">totale in LearnDash</div></div>
  <div class="tile"><div class="lab">Con 1 SOLO corso</div><div class="big">{num(len(one))}</div><div class="cap">{100*len(one)/total:.0f}% · target cross-sell</div></div>
  <div class="tile"><div class="lab">Con 2+ corsi</div><div class="big">{num(total-len(one))}</div><div class="cap">{100*(total-len(one))/total:.0f}% · base fedele</div></div>
</div>
<div class="sec">Chi ha un solo corso — per quale corso</div>
<p class="secsub">Ordinato per numero di persone. Sono i target ideali per vendere il corso successivo (costo ADV ~zero).</p>
<div class="tablewrap"><table>
<thead><tr><th class="l">Corso (unico posseduto)</th><th>Persone</th><th>% dei single</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="sec">Distribuzione: quanti corsi per persona</div>
<div style="max-width:520px">{bars}</div>
<div class="foot"><b>Fonte:</b> LearnDash (sola lettura). Conteggio per <b>linea di corso</b>: Vol.1/2/3 e sigle (EGS, CHAC, TRIM, PEPO…) contano come UNA linea; il bundle = una linea. Esclusi prodotti non-corso (Iscrizione Community = ponte migrazione, Try Before Buy = prova, bonus Sound/Tuning/Setup). {num(total)} persone con ≥1 linea, {num(len(one))} con una sola. Aggiornato settimanalmente.</div>
</div></div>"""
    return ("<!doctype html>\n<html lang=it>\n<head>\n<meta charset=utf-8>\n"
            "<meta name=viewport content=\"width=device-width, initial-scale=1\">\n"
            "<title>Varini · Corsi (LearnDash)</title>\n<style>" + CSS + "</style>\n</head>\n<body>\n"
            + body + "\n</body>\n</html>\n")


if __name__ == "__main__":
    out = os.path.join(HERE, "ld")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(build())
    open(os.path.join(out, ".htaccess"), "w", encoding="utf-8").write("DirectoryIndex index.html\nAddDefaultCharset UTF-8\n")
    print("ld/index.html generato")
