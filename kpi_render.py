#!/usr/bin/env python3
"""
Renderer della dashboard KPI (scorecard 4 clienti) — HTML auto-contenuto,
tema chiaro/scuro, nessuna dipendenza esterna.

Uso:
    python3 kpi_render.py            # legge il modello da kpi_engine (necessita token/env)
    from kpi_render import render_kpi ; html = render_kpi(model)
"""

import re
from datetime import date

import navbar

CSS = """
  :root{
    --bg:#f4f5f7; --panel:#ffffff; --panel-2:#fbfcfd;
    --ink:#141a22; --ink-2:#4a5563; --ink-3:#7b8698;
    --line:#e3e7ec; --line-2:#eef1f4;
    --accent:#2b57d6; --accent-soft:#e7edfd;
    --good:#12805c; --good-bg:#e3f3ec;
    --warn:#a5701a; --warn-bg:#faf0dc;
    --bad:#c23b34; --bad-bg:#fbe6e4;
    --shadow:0 1px 2px rgba(20,26,34,.04),0 6px 20px rgba(20,26,34,.05);
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }
  @media (prefers-color-scheme:dark){
    :root{
      --bg:#0d1017; --panel:#151a22; --panel-2:#11161d;
      --ink:#e9edf3; --ink-2:#a7b1c0; --ink-3:#6d7788;
      --line:#242c37; --line-2:#1b222b;
      --accent:#6f92f5; --accent-soft:#1b2740;
      --good:#3fcf9a; --good-bg:#12281f; --warn:#e0b25a; --warn-bg:#2c2413;
      --bad:#f0756c; --bad-bg:#2e1817;
      --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35);
    }
  }
  :root[data-theme="light"]{
    --bg:#f4f5f7; --panel:#ffffff; --panel-2:#fbfcfd;
    --ink:#141a22; --ink-2:#4a5563; --ink-3:#7b8698;
    --line:#e3e7ec; --line-2:#eef1f4;
    --accent:#2b57d6; --accent-soft:#e7edfd;
    --good:#12805c; --good-bg:#e3f3ec; --warn:#a5701a; --warn-bg:#faf0dc;
    --bad:#c23b34; --bad-bg:#fbe6e4;
    --shadow:0 1px 2px rgba(20,26,34,.04),0 6px 20px rgba(20,26,34,.05);
  }
  :root[data-theme="dark"]{
    --bg:#0d1017; --panel:#151a22; --panel-2:#11161d;
    --ink:#e9edf3; --ink-2:#a7b1c0; --ink-3:#6d7788;
    --line:#242c37; --line-2:#1b222b;
    --accent:#6f92f5; --accent-soft:#1b2740;
    --good:#3fcf9a; --good-bg:#12281f; --warn:#e0b25a; --warn-bg:#2c2413;
    --bad:#f0756c; --bad-bg:#2e1817;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35);
  }
  *{box-sizing:border-box}
  body{margin:0}
  .wrap{font-family:var(--sans);background:var(--bg);color:var(--ink);padding:40px 24px 80px;min-height:100vh;-webkit-font-smoothing:antialiased;line-height:1.5}
  .inner{max-width:1120px;margin:0 auto}
  .masthead{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:8px}
  .eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
  h1{font-size:clamp(26px,4vw,38px);line-height:1.05;letter-spacing:-.02em;margin:8px 0 6px;font-weight:750;text-wrap:balance}
  .sub{color:var(--ink-2);font-size:15px;max-width:64ch}
  .meta-row{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:14px;font-size:12.5px;color:var(--ink-3);font-family:var(--mono)}
  .meta-row b{color:var(--ink-2);font-weight:600}
  .strip{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0 34px}
  @media(max-width:760px){.strip{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:440px){.strip{grid-template-columns:1fr}}
  .tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 16px 14px;box-shadow:var(--shadow);position:relative;overflow:hidden}
  .tile::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--stat)}
  .tile .who{font-size:12px;font-weight:700;letter-spacing:.02em}
  .tile .sector{font-size:10.5px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.08em;margin-top:1px}
  .tile .big{font-family:var(--mono);font-size:27px;font-weight:600;letter-spacing:-.02em;margin-top:12px;line-height:1;font-variant-numeric:tabular-nums}
  .tile .cap{font-size:11.5px;color:var(--ink-2);margin-top:6px}
  .tile .cap b{color:var(--ink)}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);margin-bottom:20px;overflow:hidden}
  .card-h{display:flex;align-items:center;gap:12px;padding:18px 22px;border-bottom:1px solid var(--line-2);background:var(--panel-2)}
  .card-h .idx{font-family:var(--mono);font-size:12px;color:var(--ink-3);font-weight:600}
  .card-h .name{font-size:19px;font-weight:720;letter-spacing:-.01em}
  .card-h .sect{font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.08em}
  .card-h .spacer{flex:1}
  .pill{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:650;padding:4px 10px;border-radius:999px;white-space:nowrap;font-family:var(--mono)}
  .pill::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
  .p-good{color:var(--good);background:var(--good-bg)}
  .p-warn{color:var(--warn);background:var(--warn-bg)}
  .p-bad{color:var(--bad);background:var(--bad-bg)}
  .p-neutral{color:var(--ink-2);background:var(--line-2)}
  .krow.ctrl{background:linear-gradient(90deg,var(--line-2),transparent 70%);border-radius:10px;margin:4px 0}
  .krow.ctrl .kname .star-tag{color:var(--ink-3)}
  .kpis{padding:6px 10px 12px}
  .krow{display:grid;grid-template-columns:1.9fr .9fr .9fr auto;gap:10px;align-items:center;padding:13px 12px;border-bottom:1px solid var(--line-2)}
  .krow:last-child{border-bottom:none}
  .krow.star{background:linear-gradient(90deg,var(--accent-soft),transparent 70%);border-radius:10px;margin:4px 0}
  @media(max-width:640px){.krow{grid-template-columns:1fr auto;row-gap:6px}}
  .kname{font-size:14px;font-weight:600;color:var(--ink)}
  .kname .star-tag{font-size:10px;font-weight:700;color:var(--accent);letter-spacing:.06em;text-transform:uppercase;display:block;margin-bottom:2px}
  .kname small{display:block;font-weight:400;color:var(--ink-3);font-size:11.5px;margin-top:2px;line-height:1.35}
  .lbl{font-size:9.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--ink-3);font-weight:600}
  .val{font-family:var(--mono);font-size:16px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
  .act .val.hot{font-size:19px}
  .tgt .val{color:var(--ink-2)}
  .note{padding:14px 22px 18px;font-size:13px;color:var(--ink-2);background:var(--panel-2);border-top:1px solid var(--line-2);line-height:1.5}
  .note b{color:var(--ink)}
  .insight{margin:12px 22px 4px;padding:14px 16px;border:1px dashed var(--line);border-radius:12px;background:var(--panel-2)}
  .insight h4{margin:0 0 3px;font-size:13px;font-weight:700}
  .insight p{margin:0 0 12px;font-size:12px;color:var(--ink-2)}
  .bar{display:grid;grid-template-columns:152px 1fr 40px;align-items:center;gap:8px;margin:7px 0;font-size:12px}
  .bar .bl{color:var(--ink-2);font-size:11px;line-height:1.25}
  .bar .bl small{color:var(--ink-3)}
  .track{height:14px;background:var(--line-2);border-radius:7px;overflow:hidden}
  .fill{height:100%;border-radius:7px;background:var(--accent)}
  .fill.dim{background:var(--ink-3);opacity:.55}
  .bar .pc{font-family:var(--mono);font-weight:600;text-align:right;font-variant-numeric:tabular-nums}
  .dual{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px 22px 4px}
  @media(max-width:720px){.dual{grid-template-columns:1fr}}
  .mon{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--panel-2);display:flex;flex-direction:column}
  .mon-tag{font-size:9.5px;text-transform:uppercase;letter-spacing:.09em;font-weight:700;color:var(--warn);display:block;margin-bottom:3px}
  .mon h4{margin:0;font-size:13px;font-weight:700}
  .mon-p{font-size:11.5px;color:var(--ink-2);margin:4px 0 10px;line-height:1.45}
  .spark{width:100%;height:auto;display:block;overflow:visible;margin-top:auto}
  .spark-grid{stroke:var(--line);stroke-width:1}
  .spark-area{fill:var(--accent);opacity:.09}
  .spark-line{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
  .spark-line.dash{stroke-dasharray:4 3;opacity:.55}
  .spark-dot{fill:var(--accent)}
  .spark-dot.last{fill:var(--panel);stroke:var(--accent);stroke-width:2}
  .spark-v{fill:var(--ink-2);font-family:var(--mono);font-size:9px;text-anchor:middle;font-weight:600}
  .spark-x{fill:var(--ink-3);font-family:var(--sans);font-size:9px;text-anchor:middle}
  .legend{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:34px 0 8px}
  @media(max-width:640px){.legend{grid-template-columns:1fr}}
  .lg{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow)}
  .lg h3{margin:0 0 4px;font-size:13px}
  .lg .kick{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;font-weight:700;color:var(--accent)}
  .lg p{margin:6px 0 0;font-size:12.5px;color:var(--ink-2)}
  .foot{margin-top:30px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--ink-3);line-height:1.6}
  .foot b{color:var(--ink-2)}
  .drill{display:block;margin:6px 22px 18px;padding:14px 16px;border-radius:12px;background:var(--accent-soft);color:var(--accent);font-weight:700;font-size:13.5px;text-decoration:none;text-align:center;border:1px solid var(--accent)}
  .drill:hover{filter:brightness(1.04)}
  .wksel-wrap{display:inline-flex;align-items:center;gap:5px}
  #wksel{font-family:var(--mono);font-size:13px;font-weight:600;padding:5px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
""" + navbar.NAV_CSS


# ── helper di formattazione/stato ────────────────────────────────────────────
def eur(v, dec=0):
    if v is None:
        return "n.d."
    s = f"{v:,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"€{s}"


def num(v):
    return "n.d." if v is None else f"{v:,.0f}".replace(",", ".")


def pill(cls, label):
    return f'<span class="pill p-{cls}">{label}</span>'


def krow(name, sub, tgt_lbl, tgt, act_lbl, act, pill_html, star=False, hot=False):
    cls = "krow star" if star else "krow"
    tag = '<span class="star-tag">★ North Star</span>' if star else ""
    sub_html = f"<small>{sub}</small>" if sub else ""
    hotcls = " hot" if hot else ""
    return (f'<div class="{cls}"><div class="kname">{tag}{name}{sub_html}</div>'
            f'<div class="tgt"><div class="lbl">{tgt_lbl}</div><div class="val">{tgt}</div></div>'
            f'<div class="act"><div class="lbl">{act_lbl}</div><div class="val{hotcls}">{act}</div></div>'
            f'<div>{pill_html}</div></div>')


def activity_row(a):
    """Riga KPI di controllo (attività diretta del media buyer)."""
    if not a:
        return ""
    launched = a.get("launched")
    active = a.get("active")
    target = a.get("target")
    if target:
        stat = "good" if (launched or 0) >= target else "warn"
        badge = pill(stat, f"{num(launched)}/{target}")
        tgt_lbl, tgt_val = "Target/sett", f"≥ {target}"
    else:
        badge = '<span class="pill p-neutral">controllo</span>'
        tgt_lbl, tgt_val = "Lanciate/sett", num(launched)
    sub = (f"Leva diretta del media buyer. In erogazione ora: <b>{num(active)}</b> ad. "
           f"I lanci sono a ondate → leggilo come media su ~4 settimane.")
    return (f'<div class="krow ctrl"><div class="kname"><span class="star-tag">◆ Controllo — attività</span>'
            f'Ad lanciate / settimana<small>{sub}</small></div>'
            f'<div class="tgt"><div class="lbl">{tgt_lbl}</div><div class="val">{tgt_val}</div></div>'
            f'<div class="act"><div class="lbl">Lanciate</div><div class="val">{num(launched)}</div></div>'
            f'<div>{badge}</div></div>')


def tile(who, sector, big, cap, stat):
    return (f'<div class="tile" style="--stat:var(--{stat})"><div class="who">{who}</div>'
            f'<div class="sector">{sector}</div><div class="big">{big}</div>'
            f'<div class="cap">{cap}</div></div>')


def _trend_svg(trend):
    """trend = [{'label','cpa','immature'}]. Genera lo sparkline SVG."""
    pts = [(t["label"], t["cpa"], t["immature"]) for t in trend if t["cpa"] is not None]
    if len(pts) < 2:
        return '<p class="mon-p">Dati insufficienti per il trend.</p>'
    xs0, xs1, y0, y1 = 34, 320, 14, 104
    vals = [p[1] for p in pts]
    vmin, vmax = min(vals), max(vals)
    rng = (vmax - vmin) or 1
    n = len(pts)
    def X(i): return xs0 + (xs1 - xs0) * i / (n - 1)
    def Y(v): return y1 - (v - vmin) / rng * (y1 - y0)
    coords = [(X(i), Y(v)) for i, (_, v, _) in enumerate(pts)]
    # spezza in solido (fino al penultimo) + tratteggio (ultimo segmento se immaturo)
    last_imm = pts[-1][2]
    solid = coords if not last_imm else coords[:-1]
    poly_solid = " ".join(f"{x:.1f},{y:.1f}" for x, y in solid)
    area = poly_solid + f" {coords[-1][0]:.1f},{y1} {coords[0][0]:.1f},{y1}" if not last_imm \
        else " ".join(f"{x:.1f},{y:.1f}" for x, y in coords) + f" {coords[-1][0]:.1f},{y1} {coords[0][0]:.1f},{y1}"
    dash = ""
    if last_imm:
        (x1, y1p), (x2, y2p) = coords[-2], coords[-1]
        dash = f'<polyline class="spark-line dash" points="{x1:.1f},{y1p:.1f} {x2:.1f},{y2p:.1f}"/>'
    dots = ""
    vlabels = ""
    xlabels = ""
    for i, ((lab, v, imm), (x, y)) in enumerate(zip(pts, coords)):
        dcls = "spark-dot last" if imm else "spark-dot"
        dots += f'<circle class="{dcls}" cx="{x:.1f}" cy="{y:.1f}" r="{3.6 if imm else 3.2}"/>'
        anchor = ' style="text-anchor:end"' if i == n - 1 else ""
        vy = y - 8 if y > 24 else y + 14
        star = "*" if imm else ""
        vlabels += f'<text class="spark-v" x="{x:.1f}" y="{vy:.1f}"{anchor}>{v}{star}</text>'
        mese = lab.split("-")[1]
        nomi = {"01":"Gen","02":"Feb","03":"Mar","04":"Apr","05":"Mag","06":"Giu",
                "07":"Lug","08":"Ago","09":"Set","10":"Ott","11":"Nov","12":"Dic"}
        xlabels += f'<text class="spark-x" x="{x:.1f}" y="120"{anchor}>{nomi.get(mese,mese)}{star}</text>'
    return (
        '<svg class="spark" viewBox="0 0 340 128" role="img" aria-label="Andamento costo per appuntamento">'
        f'<line class="spark-grid" x1="30" y1="{y1}" x2="326" y2="{y1}"/>'
        f'<polygon class="spark-area" points="{area}"/>'
        f'<polyline class="spark-line" points="{poly_solid}"/>{dash}{dots}{vlabels}{xlabels}</svg>'
    )


def _clean_camp(name):
    """Nome campagna leggibile: toglie [ONLINE]/[TMC]/emoji e spazi doppi."""
    n = name
    for junk in ["[ONLINE]", "[TMC]", "🟥"]:
        n = n.replace(junk, "")
    n = re.sub(r"\s+", " ", n).strip(" |")
    return n


def _module_bars(modules, min_lead=15, top=8):
    """Spaccato per singola campagna/modulo (tasso lead→appuntamento)."""
    items = [m for m in modules if m["lead"] >= min_lead and "?" not in m["campaign"]]
    if not items:
        return '<p class="mon-p">Nessuna campagna con dati sufficienti nella coorte.</p>'
    items = sorted(items, key=lambda x: -x["rate"])[:top]
    mx = max(m["rate"] for m in items) or 1
    rows = ""
    for m in items:
        w = 100 * m["rate"] / mx
        dim = "" if m["type"] in ("Landing", "Qualificati") else " dim"
        rows += (f'<div class="bar"><span class="bl">{_clean_camp(m["campaign"])} '
                 f'<small>({m["lead"]})</small></span>'
                 f'<span class="track"><span class="fill{dim}" style="width:{w:.0f}%"></span></span>'
                 f'<span class="pc">{m["rate"]:.0f}%</span></div>')
    return rows


# ── contenuto (strip + 4 card) — dipende dalla settimana ──────────────────────
def _cards(m: dict) -> str:
    wpm = m["weeks_per_month"]
    def wk(x):  # target settimanale da mensile
        return x / wpm

    B, V, P, D = m["balducci"], m["varini"], m["pontoni"], m["didomenico"]

    # ---- Balducci ----
    b_real_pd = B.get("real_persons_day")
    b_pd = b_real_pd if b_real_pd is not None else B["persons_day"]
    b_src = "reale (WooCommerce)" if b_real_pd is not None else "Meta Acquisto_unico"
    b_stat = "good" if b_pd >= 45 else ("warn" if b_pd >= 25 else "bad")
    b_pct = round(100 * b_pd / 50) if b_pd else 0
    cpa_prod = B.get("cpa_display") or B["cpa_product"]  # riferimento fisso €9
    cpa_pill = "good" if (cpa_prod is not None and cpa_prod <= 13) else "warn"
    b_spend_pct = round(100 * B["spend"] / wk(m["targets"]["balducci_spend"])) if B["spend"] else 0
    cpa_real = round(B["spend"] / B["real_customers"], 2) if B.get("real_customers") else None
    if B.get("real_customers") is not None:
        real_row = krow("Reale (Woo) vs tracciato (Meta)", "Incasso reale " + eur(B.get("real_revenue")) + " · <b>CPA reale (spesa ÷ clienti Woo) " + eur(cpa_real, 2) + "</b> · clienti unici veri (per email) vs evento Meta Acquisto_unico.", "Meta (Acq.unico)", num(B["persons"]), "Reale (Woo)", num(B["real_customers"]), pill("good", "CPA reale " + eur(cpa_real, 0)))
    else:
        real_row = krow("Reale (WooCommerce)", "Connessione Woo non disponibile.", "—", "—", "Stato", "n.d.", pill("warn", "assente"))
    balducci = f"""
  <article class="card">
    <div class="card-h"><span class="idx">03</span><span class="name">Balducci</span><span class="sect">Integratori naturali</span><span class="spacer"></span>{pill(b_stat,f"{b_pct}% del volume")}</div>
    <div class="kpis">
      {krow("Clienti unici / giorno","North Star: 50 <b>persone</b>/giorno. Attuale = "+b_src+"; "+num(B.get("real_customers") or B["persons"])+" persone/sett.","Obiettivo","50/gg","Attuale",f"{b_pd:g}/gg",pill(b_stat,f"{b_pct}%"),star=True,hot=True)}
      {krow("CPA che monitoro su Meta (per acquisto)","Media account (riferimento €9). Per persona sale a ~"+eur(B["cpa_person"],2)+".","Tetto","≤ €13","Attuale",eur(cpa_prod,0),pill(cpa_pill,"Ottimo" if cpa_pill=="good" else "Al limite"))}
      {real_row}
      {krow("Spesa / settimana verso 20k/mese","",  "Target",eur(wk(m["targets"]["balducci_spend"])),"Attuale",eur(B["spend"]),pill("warn",f"{b_spend_pct}%"))}
      {activity_row(B.get("activity"))}
    </div>
  </article>"""

    # ---- Varini ----
    v_target_wk = wk(m["targets"]["varini_profit"])
    v_pct = round(100 * V["profit"] / v_target_wk) if V.get("profit") else 0
    v_stat = "good" if v_pct >= 100 else ("warn" if v_pct >= 70 else "bad")
    roas_pill = "good" if (V.get("roas") or 0) >= 1 else "bad"
    varini = f"""
  <article class="card">
    <div class="card-h"><span class="idx">02</span><span class="name">Varini</span><span class="sect">Corsi chitarra · GuitarTribe</span><span class="spacer"></span>{pill(v_stat,f"{v_pct}% del target")}</div>
    <div class="kpis">
      {krow("Profitto netto / settimana","Incasso reale (WooCommerce) − spesa Meta. Sotto il target si lavora gratis.","Obiettivo","≥ "+eur(v_target_wk),"Attuale",eur(V.get("profit")),pill(v_stat,f"{v_pct}%"),star=True,hot=True)}
      {krow("ROAS reale (WooCommerce)","Break-even a 1,0 (COGS ~0 sui corsi). Sopra = spesa scalabile.","Break-even","≥ 1,0","Attuale",str(V.get("roas") or "n.d.").replace(".",","),pill(roas_pill,"Scalabile" if roas_pill=="good" else "Sotto"))}
      {krow("Fedeltà tracking (Meta vs reale)","Meta dichiara "+num(V.get("meta_purchases"))+" acquisti; ordini reali Woo "+num(V.get("orders"))+" (di cui "+num(V.get("meta_orders"))+" attribuiti a Meta).","Meta dice",num(V.get("meta_purchases")),"Reali Woo",num(V.get("orders")),pill("warn","Meta gonfia"))}
      {activity_row(V.get("activity"))}
    </div>
  </article>"""

    # ---- Pontoni ----
    cpl = P["cpl"]
    cpl_pill = "good" if (cpl is not None and cpl <= 16) else "warn"
    q = P["quality_pct"]
    q_disp = f"~{q}%" if q is not None else "n.d."
    q_pill = pill("warn","Mix da spostare") if (q is None or q < 50) else pill("good","OK")
    sp_month = P["spend_month"]
    sp_pill_pct = round(100 * sp_month / m["targets"]["pontoni_spend"]) if sp_month else 0
    if P.get("modules"):
        panel_right = (f'<div class="insight" style="margin:0"><h4>Spaccato per modulo (leva sulla qualità)</h4>'
                       f'<p>Tasso lead→appuntamento per campagna (coorte matura, ≥15 lead). Tra parentesi i lead.</p>'
                       f'{_module_bars(P["modules"])}</div>')
    else:
        panel_right = f'<div class="insight" style="margin:0"><h4>Spaccato per modulo</h4><p>Dati Odoo temporaneamente non disponibili.<br><small>{P.get("odoo_error","")}</small></p></div>'
    if P.get("trend"):
        chart = _trend_svg(P["trend"])
        mon = (f'<div class="mon"><span class="mon-tag">◑ Dato monitorato · non è un obiettivo del media buyer</span>'
               f'<h4>Costo per appuntamento — andamento</h4>'
               f'<p class="mon-p">Dipende anche dalla lavorazione lead del centro. Utile come contesto.</p>{chart}'
               f'<p class="mon-p" style="margin:8px 0 0;font-size:10.5px;color:var(--ink-3)">€ per appuntamento · *ultimo mese in maturazione. Fonte: Odoo + spesa Meta.</p></div>')
    else:
        mon = '<div class="mon"><span class="mon-tag">◑ Dato monitorato</span><h4>Costo per appuntamento — andamento</h4><p class="mon-p">Dati Odoo temporaneamente non disponibili.</p></div>'
    pontoni = f"""
  <article class="card">
    <div class="card-h"><span class="idx">01</span><span class="name">Pontoni</span><span class="sect">Centri acustici</span><span class="spacer"></span>{cpl_pill_badge(cpl_pill)}</div>
    <div class="kpis">
      {krow("Qualità del lead: % da campagne ad alta conversione","Landing + moduli qualificati fissano appuntamenti fino a 3× le Lead ADS. Dove va il budget lo controlli tu.","Obiettivo","≥ 50%","Attuale",q_disp,q_pill,star=True,hot=True)}
      {krow("Costo per lead tracciato","Obiettivo dichiarato.","Obiettivo","≤ €16","Attuale",eur(cpl,2),pill(cpl_pill,"Raggiunto" if cpl_pill=="good" else "Sopra"))}
      {krow("Volume lead / settimana","","Riferimento","—","Attuale",num(P["leads"]),pill("good","Solido"))}
      {krow("Spesa / mese","Target €20k/mese.","Target","€20k","Attuale","~"+eur(sp_month),pill("warn",f"{sp_pill_pct}%"))}
      {activity_row(P.get("activity"))}
    </div>
    <div class="dual">{mon}{panel_right}</div>
    <a class="drill" href="pontoni/">📊 Apri lo spaccato moduli — appuntamenti fissati per settimana + cumulativo →</a>
  </article>"""

    # ---- Di Domenico ----
    d_pct = round(100 * D["purchases"] / wk(m["targets"]["didom_purchases"])) if D["purchases"] else 0
    d_stat = "good" if d_pct >= 90 else ("warn" if d_pct >= 70 else "bad")
    cpa = D["cpa"]
    cpa_pill_d = "good" if (cpa is not None and cpa <= 65) else "bad"
    roas = D["roas"]
    roas_pill_d = "good" if (roas is not None and roas >= 0.7) else "bad"
    sp_pill_d = "good" if abs(D["spend"] - wk(m["targets"]["didom_spend"])) < wk(m["targets"]["didom_spend"]) * 0.2 else "warn"
    didom = f"""
  <article class="card">
    <div class="card-h"><span class="idx">04</span><span class="name">Di Domenico</span><span class="sect">Editoria B2B · Studio GD</span><span class="spacer"></span>{pill(d_stat,f"{d_pct}% del target")}</div>
    <div class="kpis">
      {krow("Acquirenti libro / settimana","Far entrare gente nell'ecosistema. Il backend consulenze è del cliente.","Obiettivo","~"+f"{wk(m['targets']['didom_purchases']):.0f}","Attuale",num(D["purchases"]),pill(d_stat,f"{d_pct}%"),star=True,hot=True)}
      {krow("CPA (costo per acquisto)","","Obiettivo","≤ €65","Attuale",eur(cpa,2),pill(cpa_pill_d,"OK" if cpa_pill_d=="good" else "Sopra"))}
      {krow("Spesa / settimana","","Obiettivo",eur(wk(m["targets"]["didom_spend"])),"Attuale",eur(D["spend"]),pill(sp_pill_d,"In linea" if sp_pill_d=="good" else "Fuori"))}
      {krow("ROAS front-end (soglia, non profitto)","Libro €"+f"{D['book_price']:.0f}"+", monetizzazione a valle (consulenze).","Soglia","≥ 0,7","Attuale",str(roas or "n.d.").replace(".",","),pill(roas_pill_d,"OK" if roas_pill_d=="good" else "Sotto soglia"))}
      {activity_row(D.get("activity"))}
    </div>
  </article>"""

    # ---- strip ----
    strip = (
        tile("Pontoni","Centri acustici",eur(cpl,2),"costo/lead · <b>target €16</b> · qualità mix da alzare","good" if cpl_pill=="good" else "warn")
        + tile("Varini","Corsi chitarra",eur(V.get("profit")),f"profitto/sett · <b>{v_pct}% del target</b>",v_stat)
        + tile("Balducci","Integratori",f"{b_pd:g}/gg","persone reali/gg · <b>target 50</b> · CPA "+eur(cpa_prod,0),b_stat)
        + tile("Di Domenico","Editoria B2B",f"{D['purchases']}/sett",f"acquisti · <b>{d_pct}% del target</b>",d_stat)
    )

    legend = """
  <section class="legend">
    <div class="lg"><div class="kick">Livello 1 — controllo</div><h3>KPI di controllo</h3><p>CPA/CPL, % budget sui vincenti, disciplina di tracking, velocità di test, <b>traiettoria</b> verso il target: guidati dal media buyer.</p></div>
    <div class="lg"><div class="kick">Livello 2 — business</div><h3>KPI di risultato</h3><p>Appuntamenti fissati (Pontoni), consulenze chiuse (Di Domenico), LTV: dipendono anche dal cliente.</p></div>
  </section>"""

    foot = (f'<div class="foot"><b>Fonti:</b> Meta Ads · WooCommerce (Varini) · Odoo sola lettura (Pontoni). '
            f'Balducci per-persona via evento Acquisto_unico. Di Domenico ROAS su libro €{D["book_price"]:.0f}. '
            f'Costo/appuntamento Pontoni: dato di contesto (coorte matura), non un obiettivo del media buyer. '
            f'Aggiornato automaticamente ogni lunedì.</div>')

    return (f'<section class="strip">{strip}</section>\n{pontoni}\n{varini}\n{balducci}\n{didom}')


def _legend_foot(m):
    legend = """
  <section class="legend">
    <div class="lg"><div class="kick">Livello 1 — controllo</div><h3>KPI di controllo</h3><p>CPA/CPL, % budget sui vincenti, disciplina di tracking, velocità di test, <b>traiettoria</b> verso il target: guidati dal media buyer.</p></div>
    <div class="lg"><div class="kick">Livello 2 — business</div><h3>KPI di risultato</h3><p>Appuntamenti fissati (Pontoni), consulenze chiuse (Di Domenico), LTV: dipendono anche dal cliente.</p></div>
  </section>"""
    foot = ('<div class="foot"><b>Fonti:</b> Meta Ads · WooCommerce (Varini) · Odoo sola lettura (Pontoni). '
            'Balducci per-persona via evento Acquisto_unico. Di Domenico ROAS su libro €37. '
            'Costo/appuntamento Pontoni: dato di contesto (coorte matura), non un obiettivo del media buyer. '
            'Aggiornato automaticamente ogni giorno.</div>')
    return legend + foot


def render_kpi(m: dict) -> str:
    """Scorecard singola settimana (compatibilità)."""
    head = f"""<div class="wrap"><div class="inner">
  {navbar.nav_html("/tommaso/kpi/")}
  <header class="masthead">
    <div class="eyebrow">Media Buying · Scorecard settimanale</div>
    <h1>KPI di riferimento — 4 clienti</h1>
    <p class="sub">Un North Star per cliente (il numero che vale i soldi) e i KPI di controllo a supporto.</p>
    <div class="meta-row"><span><b>Settimana:</b> {_fmt(m["week_start"])} – {_fmt(m["week_end"])}</span></div>
  </header>
  {_cards(m)}
  {_legend_foot(m)}
</div></div>"""
    return f"<style>{CSS}</style>\n{head}"


def _merge_week(latest: dict, wdata: dict) -> dict:
    """Modello per una settimana: numeri Meta/Woo della settimana + parte Odoo Pontoni (coorte, condivisa)."""
    P = dict(wdata["pontoni"])  # spend, leads, cpl (settimana)
    lp = latest["pontoni"]
    P["spend_month"] = round(P["spend"] * latest["weeks_per_month"], 0)
    for k in ("quality_pct", "types", "modules", "trend", "odoo_error"):
        P[k] = lp.get(k)
    return {"targets": latest["targets"], "weeks_per_month": latest["weeks_per_month"],
            "balducci": wdata["balducci"], "varini": wdata["varini"],
            "pontoni": P, "didomenico": wdata["didomenico"]}


def render_kpi_multiweek(latest: dict, series: dict) -> str:
    """Scorecard con SELEZIONATORE settimana: N settimane pre-renderizzate, JS ne mostra una."""
    weeks = series["weeks"]  # dal più vecchio al più recente
    default = len(weeks) - 1
    opts = "".join(
        f'<option value="{i}"{" selected" if i == default else ""}>{w} ({series["data"][w]["range"]})</option>'
        for i, w in enumerate(weeks))
    views = ""
    for i, w in enumerate(weeks):
        cards = _cards(_merge_week(latest, series["data"][w]))
        style = "" if i == default else ' style="display:none"'
        views += f'<section class="weekview" data-w="{i}"{style}>{cards}</section>'
    gen = latest.get("generated_at") or ""
    head = f"""<div class="wrap"><div class="inner">
  {navbar.nav_html("/tommaso/kpi/")}
  <header class="masthead">
    <div class="eyebrow">Media Buying · Scorecard settimanale</div>
    <h1>KPI di riferimento — 4 clienti</h1>
    <p class="sub">Un North Star per cliente e i KPI di controllo. Scegli la settimana dal menu.</p>
    <div class="meta-row">
      <span class="wksel-wrap"><b>Settimana:</b>
        <select id="wksel">{opts}</select></span>
      <span><b>Generato:</b> {gen[:16].replace("T"," ")}</span>
    </div>
  </header>
  <div id="weekviews">{views}</div>
  {_legend_foot(latest)}
</div></div>
<script>
const sel=document.getElementById('wksel');
function showWeek(){{
  const i=sel.value;
  document.querySelectorAll('.weekview').forEach(v=>{{v.style.display = (v.dataset.w===i)?'':'none';}});
}}
sel.addEventListener('change', showWeek); showWeek();
</script>"""
    return f"<style>{CSS}</style>\n{head}"


def cpl_pill_badge(cpl_pill):
    return pill("good","Obiettivi lead centrati") if cpl_pill == "good" else pill("warn","In lavorazione")


def _meta_purch(V):
    # acquisti "dichiarati" da Meta ~ non memorizzati qui; usiamo orders reali se manca
    return V.get("orders")


def _fmt(iso):
    g, m2, d = iso.split("-")
    return f"{int(d)}/{int(m2)}"


if __name__ == "__main__":
    import os, sys
    from kpi_engine import build_kpi
    token = os.environ.get("META_TOKEN")
    if not token:
        from store import get_meta_token
        token = get_meta_token()
    ref = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    model = build_kpi(ref, token)
    print(render_kpi(model))
