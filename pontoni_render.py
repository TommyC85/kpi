#!/usr/bin/env python3
"""Genera la pagina interattiva 'Pontoni — Spaccato moduli' da pontoni_moduli_data.json.
Selezionatore settimana + numeri assoluti (lead entrati / appuntamenti fissati) per modulo
della settimana e cumulativi dalla creazione, solo moduli attivi, + costo/appuntamento per fonte.
"""
import json, os

CSS = """
:root{--bg:#f4f5f7;--panel:#fff;--panel-2:#fbfcfd;--ink:#141a22;--ink-2:#4a5563;--ink-3:#7b8698;
--line:#e3e7ec;--line-2:#eef1f4;--accent:#2b57d6;--accent-soft:#e7edfd;--good:#12805c;--good-bg:#e3f3ec;
--warn:#a5701a;--warn-bg:#faf0dc;--mono:ui-monospace,"SF Mono",Menlo,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;--shadow:0 1px 2px rgba(20,26,34,.05),0 6px 20px rgba(20,26,34,.05)}
@media(prefers-color-scheme:dark){:root{--bg:#0d1017;--panel:#151a22;--panel-2:#11161d;--ink:#e9edf3;--ink-2:#a7b1c0;--ink-3:#6d7788;--line:#242c37;--line-2:#1b222b;--accent:#6f92f5;--accent-soft:#1b2740;--good:#3fcf9a;--good-bg:#12281f;--warn:#e0b25a;--warn-bg:#2c2413;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35)}}
:root[data-theme=light]{--bg:#f4f5f7;--panel:#fff;--panel-2:#fbfcfd;--ink:#141a22;--ink-2:#4a5563;--ink-3:#7b8698;--line:#e3e7ec;--line-2:#eef1f4;--accent:#2b57d6;--accent-soft:#e7edfd;--good:#12805c;--good-bg:#e3f3ec;--warn:#a5701a;--warn-bg:#faf0dc}
:root[data-theme=dark]{--bg:#0d1017;--panel:#151a22;--panel-2:#11161d;--ink:#e9edf3;--ink-2:#a7b1c0;--ink-3:#6d7788;--line:#242c37;--line-2:#1b222b;--accent:#6f92f5;--accent-soft:#1b2740;--good:#3fcf9a;--good-bg:#12281f;--warn:#e0b25a;--warn-bg:#2c2413}
*{box-sizing:border-box}body{margin:0}
.wrap{font-family:var(--sans);background:var(--bg);color:var(--ink);padding:36px 20px 80px;min-height:100vh;-webkit-font-smoothing:antialiased}
.inner{max-width:1080px;margin:0 auto}
.head{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;justify-content:space-between;border-bottom:2px solid var(--ink);padding-bottom:16px}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
h1{font-size:clamp(24px,3.5vw,34px);margin:6px 0 2px;letter-spacing:-.02em;font-weight:750}
.sub{color:var(--ink-2);font-size:14px;margin:0}
.sel{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-end}
.wk{display:flex;flex-direction:column;gap:4px}
.wk label{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--ink-3);font-weight:700}
.wk select{font-family:var(--mono);font-size:15px;font-weight:600;padding:9px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);box-shadow:var(--shadow);cursor:pointer}
.upd{font-size:11px;color:var(--ink-3);margin-top:7px;display:flex;align-items:center;gap:8px;font-family:var(--mono)}
.upd button{font-family:var(--sans);font-size:11px;font-weight:600;padding:4px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--accent);cursor:pointer}
.upd button:hover{background:var(--accent-soft)}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:24px 0}
@media(max-width:560px){.cards{grid-template-columns:1fr}}
.cpa{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.cpa::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--stat)}
.cpa .lab{font-size:12px;font-weight:700}.cpa .lab span{color:var(--ink-3);font-weight:500}
.cpa .big{font-family:var(--mono);font-size:30px;font-weight:600;letter-spacing:-.02em;margin-top:8px;line-height:1}
.cpa .wkval{font-size:12px;color:var(--ink-2);margin-top:6px;font-family:var(--mono)}
.tablewrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;min-width:720px}
thead th{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:700;padding:12px 12px;text-align:right;border-bottom:1px solid var(--line);background:var(--panel-2);white-space:nowrap}
thead th.l{text-align:left}
thead tr.grp th{font-size:10px;color:var(--accent);border-bottom:none;padding-bottom:2px}
tbody td{padding:11px 12px;text-align:right;font-family:var(--mono);font-size:14px;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--line-2)}
tbody td.l{text-align:left;font-family:var(--sans);font-weight:600}
tbody td .src{display:block;font-size:10.5px;font-weight:500;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em}
tbody tr:hover{background:var(--panel-2)}
tbody tr.tot td{border-top:2px solid var(--line);border-bottom:none;font-weight:700;background:var(--panel-2)}
.pct{color:var(--ink-3);font-size:12px}
.sep{border-left:1px solid var(--line)}
.tag{display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;font-family:var(--mono)}
.tag.land{color:var(--good);background:var(--good-bg)}.tag.lead{color:var(--warn);background:var(--warn-bg)}
.foot{margin-top:22px;font-size:12px;color:var(--ink-3);line-height:1.6}.foot b{color:var(--ink-2)}
.note{margin-top:14px;padding:12px 16px;border:1px dashed var(--line);border-radius:12px;background:var(--panel-2);font-size:12.5px;color:var(--ink-2);line-height:1.5}
"""
import navbar
CSS = CSS + navbar.NAV_CSS

def build(data: dict) -> str:
    weeks = data["weeks"]
    default = len(weeks) - 2 if len(weeks) >= 2 else len(weeks) - 1
    body = f"""<div class="wrap"><div class="inner">
{navbar.nav_html("/tommaso/kpi/pontoni/")}
<div class="head">
  <div>
    <div class="eyebrow">Pontoni · Centri acustici</div>
    <h1>Spaccato moduli — appuntamenti</h1>
    <p class="sub">Lead entrati e <b>appuntamenti fissati</b> per modulo. Solo moduli attivi. Numeri assoluti.</p>
  </div>
  <div class="sel">
    <div class="wk"><label for="wksel">Settimana</label>
      <select id="wksel">{"".join(f'<option value="{i}"{" selected" if i==default else ""}>{w}</option>' for i,w in enumerate(weeks))}</select></div>
    <div class="wk"><label for="msel">Mese</label>
      <select id="msel">{"".join(f'<option value="{i}"{" selected" if i==len(data["months"])-1 else ""}>{lab}</option>' for i,(k,lab) in enumerate(data["months"]))}</select></div>
    <div class="upd">Aggiornato: {data['generated']} <button id="refresh" title="Ricarica l'ultimo dato generato (rigenerato ogni giorno)">🔄 Aggiorna</button></div>
  </div>
</div>

<div class="cards">
  <div class="cpa" style="--stat:var(--good)"><div class="lab">Costo per appuntamento · <span>Landing</span></div>
    <div class="big" id="cpaLandCum">–</div><div class="wkval" id="cpaLandWk">settimana: –</div></div>
  <div class="cpa" style="--stat:var(--warn)"><div class="lab">Costo per appuntamento · <span>Lead ADS</span></div>
    <div class="big" id="cpaLeadCum">–</div><div class="wkval" id="cpaLeadWk">settimana: –</div></div>
</div>

<div class="tablewrap"><table>
  <thead>
    <tr class="grp"><th class="l"></th><th></th><th colspan="2" id="wkhead">Settimana</th><th colspan="2" id="mhead" class="sep">Mese</th><th colspan="4" class="sep">Cumulativo (dalla creazione)</th><th class="sep">Costo/app</th></tr>
    <tr><th class="l">Modulo</th><th class="l">Fonte</th><th>Lead</th><th>Fissati</th><th class="sep">Lead</th><th>Fissati</th><th class="sep">Lead</th><th>Fissati</th><th>Presentati</th><th>%</th><th class="sep">€/app (modulo)</th></tr>
  </thead>
  <tbody id="rows"></tbody>
</table></div>

<div class="note"><b>Definizione:</b> "appuntamento fissato" = un appuntamento <b>prenotato</b> (qualsiasi esito: presentato, no-show, annullato). La colonna <b>Presentati</b> (solo nel cumulativo) = di quelli, chi si è poi <b>presentato</b>. Fonte: esito appuntamento Odoo. ·
<b>Maturità:</b> le settimane recenti hanno pochi appuntamenti perché i lead sono appena entrati e non ancora lavorati → guarda settimane di 3+ settimane fa per numeri stabili; il <b>cumulativo</b> è sempre affidabile.</div>

<div class="foot"><b>Fonti:</b> Odoo (appuntamenti fissati, sola lettura) + Meta (spesa). <b>€/app (modulo)</b> = spesa Meta di quel modulo ÷ appuntamenti fissati del modulo (costo reale per modulo, cumulativo). Le due card in alto sono il costo medio per fonte. "n.d." = spesa Meta non attribuibile al modulo per nome. Generato {data['generated']}.</div>

<script>
const DATA = {json.dumps(data, ensure_ascii=False)};
function eur(v){{return v==null?'–':'€'+v.toLocaleString('it-IT')}}
function render(){{
  const wi = +document.getElementById('wksel').value;
  const wk = DATA.weeks[wi];
  const mi = +document.getElementById('msel').value;
  const mkey = DATA.months[mi][0];
  document.getElementById('wkhead').textContent = 'Settimana ' + wk;
  document.getElementById('mhead').textContent = DATA.months[mi][1];
  const cs = DATA.cost_source;
  document.getElementById('cpaLandCum').textContent = eur(cs.cum['Landing'].cpa);
  document.getElementById('cpaLeadCum').textContent = eur(cs.cum['Lead ADS'].cpa);
  const wl = cs.weekly[wk] || {{}};
  document.getElementById('cpaLandWk').textContent = 'settimana: ' + eur((wl['Landing']||{{}}).cpa) + ' · ' + ((wl['Landing']||{{}}).appt||0) + ' app';
  document.getElementById('cpaLeadWk').textContent = 'settimana: ' + eur((wl['Lead ADS']||{{}}).cpa) + ' · ' + ((wl['Lead ADS']||{{}}).appt||0) + ' app';
  let tL=0,tA=0,tML=0,tMA=0,tCL=0,tCA=0,tCP=0, rows='';
  for(const m of DATA.modules){{
    const w = m.weekly[wk] || {{lead:0,appt:0}};
    const mo = m.monthly[mkey] || {{lead:0,appt:0}};
    const cl = m.cum.lead, ca = m.cum.appt, cp = m.cum.pres||0, pct = cl? Math.round(100*ca/cl):0;
    const tag = m.source==='Landing'?'<span class="tag land">Landing</span>':'<span class="tag lead">Lead ADS</span>';
    rows += `<tr><td class="l">${{m.name.split('|')[0].trim()}}</td><td class="l">${{tag}}</td>`+
      `<td>${{w.lead}}</td><td>${{w.appt}}</td>`+
      `<td class="sep">${{mo.lead}}</td><td>${{mo.appt}}</td>`+
      `<td class="sep">${{cl}}</td><td>${{ca}}</td><td>${{cp}}</td><td class="pct">${{pct}}%</td>`+
      `<td class="sep">${{eur(m.cum.cpa)}}</td></tr>`;
    tL+=w.lead;tA+=w.appt;tML+=mo.lead;tMA+=mo.appt;tCL+=cl;tCA+=ca;tCP+=cp;
  }}
  rows += `<tr class="tot"><td class="l">Totale attivi</td><td></td><td>${{tL}}</td><td>${{tA}}</td>`+
    `<td class="sep">${{tML}}</td><td>${{tMA}}</td>`+
    `<td class="sep">${{tCL}}</td><td>${{tCA}}</td><td>${{tCP}}</td><td class="pct">${{tCL?Math.round(100*tCA/tCL):0}}%</td><td class="sep"></td></tr>`;
  document.getElementById('rows').innerHTML = rows;
}}
document.getElementById('wksel').addEventListener('change', render);
document.getElementById('msel').addEventListener('change', render);
document.getElementById('refresh').addEventListener('click', function(){{ location.href = location.pathname + '?_=' + Date.now(); }});
render();
</script>
</div></div>"""
    return ("<!doctype html>\n<html lang=it>\n<head>\n<meta charset=utf-8>\n"
            "<meta name=viewport content=\"width=device-width, initial-scale=1\">\n"
            "<title>Pontoni — Spaccato moduli</title>\n<style>" + CSS + "</style>\n</head>\n<body>\n"
            + body + "\n</body>\n</html>\n")

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    data = json.load(open(os.path.join(here, "pontoni_moduli_data.json")))
    out_dir = os.path.join(here, "pontoni")
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(build(data))
    open(os.path.join(out_dir, ".htaccess"), "w", encoding="utf-8").write(
        "DirectoryIndex index.html\nAddDefaultCharset UTF-8\n")
    print("pontoni/index.html generato")
