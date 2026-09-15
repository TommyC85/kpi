#!/usr/bin/env python3
"""
Saturazione del pubblico per adset — la FTI ricostruita.

PERCHÉ NON LA FTI DI META. `first_time_impression_ratio` esiste in Ads Manager ma
il Marketing API la rifiuta ("not valid for fields param"). Qui la si ricostruisce:
il `reach` è deduplicato sull'intervallo richiesto, quindi

    persone nuove della settimana = reach(ancora → fine settimana)
                                  − reach(ancora → fine settimana precedente)

e la quota di erogazione andata a gente mai raggiunta prima è

    FTI ≈ persone nuove ÷ impression della settimana

⚠️ È UN PROXY, non il numero di Ads Manager. Meta conta le *impression* a chi non
aveva mai visto l'annuncio; qui si contano le *persone* nuove. Chi arriva oggi
spesso vede l'annuncio più volte nello stesso giorno, quindi questo numero sta
sotto quello di Meta. Per leggere una tendenza va bene, per citare un valore
assoluto no — la pagina lo dichiara.

PERCHÉ LA FREQUENZA NON BASTA. `frequency` è impression ÷ reach *dentro* la
finestra: non distingue "vedo sempre le stesse persone" da "ne trovo di nuove
ogni giorno". Sui dati Pontoni si vedono adset con frequenza ferma a 1,5 e FTI
dimezzata in due settimane: la frequenza non se ne accorge.

PERCHÉ NIENTE ARCHIVIO. Un giorno concluso non cambia più, quindi la stessa
domanda posta oggi o fra un mese dà la stessa risposta: la storia si ricostruisce
dalla fonte a ogni giro, senza tabella da tenere allineata. Costa
(SETTIMANE + 1) + SETTIMANE chiamate per account, una volta a settimana.

⚠️ RISULTATO DELLA VERIFICA (2026-09-15, Pontoni, 12 settimane, 19 adset, n=187).
NON è agganciato alla dashboard, e il motivo è che la FTI non fa quello che si
sperava: non anticipa il peggioramento del costo.

    ΔFTI → ΔCPR stessa settimana    r = +0,13
    ΔFTI → ΔCPR una settimana dopo  r = −0,13     rumore intorno a zero
    ΔFTI → ΔCPR due settimane dopo  r = +0,13

Quando la FTI cala di oltre il 15%, il CPR SCENDE >10% nel 45% dei casi e sale
nel 25%: mediana −8%. Il calo di FTI è l'algoritmo che concentra l'erogazione
sulla fetta che risponde, non il pubblico che si esaurisce.

Nessun altro segnale testato batte la base (CPR sale >10% nel 34% delle settimane):
frequenza >2,0 → 31% · CPM in salita >15% → 23% · adset oltre 26 settimane → 29% ·
spesa in calo >20% → 40% · FTI <8% → 50% ma su soli 10 casi.

L'unico risultato robusto è di segno opposto: **"CPR già salito la settimana
prima" → risale solo nel 16%**, metà della base. A questi volumi la settimana è
dominata dal rumore e torna verso la media: un allarme settimanale suonerebbe
quasi sempre a vuoto, e reagire a una brutta settimana è controproducente.

Da ritestare con più storia, o su unità più grandi (campagna invece di adset) e
finestre più lunghe (4 settimane invece di 1), dove il rumore pesa meno.

Env: META_TOKEN, oppure token dal collegamento OAuth su Supabase.
"""

import json
from datetime import date, datetime, timedelta

import certifi
import requests

API = "https://graph.facebook.com/v22.0"

# Quante settimane chiuse mostrare. 12 ≈ un trimestre: abbastanza per vedere una
# curva di saturazione senza che la finestra di reach cumulativo diventi enorme.
WEEKS = 12

# Quanto indietro può spingersi l'ancora del reach cumulativo. Oltre, le finestre
# diventano lunghissime e Meta stima il reach invece di contarlo.
MAX_ANCHOR_DAYS = 540

LEAD_KEYS = ["lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"]
PURCHASE_KEYS = ["offsite_conversion.fb_pixel_purchase", "purchase", "omni_purchase"]


def _get(url, params, tries=4):
    """GET con retry: Meta ogni tanto risponde HTML o vuoto e .json() esplode."""
    import time
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, verify=certifi.where(), timeout=120)
            j = r.json()
            if "error" in j:
                raise RuntimeError(j["error"].get("message", "")[:200])
            return j
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Meta non risponde dopo {tries} tentativi: {last}")


def week_bounds(n=WEEKS, ref=None):
    """Le ultime n settimane CHIUSE (lunedì→domenica), dalla più vecchia.

    Solo settimane concluse: la corrente è parziale e farebbe sembrare un crollo
    di FTI quello che è solo un mercoledì.
    """
    ref = ref or date.today()
    last_sunday = ref - timedelta(days=ref.isoweekday() % 7 or 7)
    out = []
    for i in range(n - 1, -1, -1):
        u = last_sunday - timedelta(days=7 * i)
        out.append((u - timedelta(days=6), u))
    return out


def fetch_adsets(account, token):
    """Anagrafica adset: serve `created_time` per l'asse 'età dell'adset'."""
    out = {}
    url = f"{API}/{account}/adsets"
    p = {"access_token": token, "limit": 200,
         "fields": "id,name,created_time,effective_status,campaign{name}"}
    while url:
        j = _get(url, p)
        for a in j.get("data", []):
            out[a["id"]] = {
                "name": a.get("name", ""),
                "campaign": (a.get("campaign") or {}).get("name", ""),
                "status": a.get("effective_status", ""),
                "created": (a.get("created_time") or "")[:10],
            }
        url = (j.get("paging") or {}).get("next")
        p = {}          # il next porta già i parametri
    return out


def _insights(account, token, since, until, fields):
    p = {"access_token": token, "level": "adset", "limit": 500, "fields": "adset_id," + fields,
         "time_range": json.dumps({"since": since, "until": until})}
    rows, url = {}, f"{API}/{account}/insights"
    while url:
        j = _get(url, p)
        for d in j.get("data", []):
            rows[d["adset_id"]] = d
        url = (j.get("paging") or {}).get("next")
        p = {}
    return rows


def _act(row, keys):
    acts = {a["action_type"]: float(a["value"]) for a in (row.get("actions") or [])}
    for k in keys:
        if k in acts:
            return int(round(acts[k]))
    return 0


def build(account, token, weeks=WEEKS, result_keys=None, ref=None):
    """Serie settimanale per adset: FTI ricostruita, frequenza, costo per risultato."""
    result_keys = result_keys or LEAD_KEYS
    bounds = week_bounds(weeks, ref)
    meta = fetch_adsets(account, token)

    # Ancora del cumulativo: il lancio dell'adset più vecchio, con un tetto.
    created = [v["created"] for v in meta.values() if v["created"]]
    floor = (date.today() - timedelta(days=MAX_ANCHOR_DAYS)).isoformat()
    anchor = max(min(created) if created else floor, floor)

    # Un confine in più PRIMA della prima settimana: senza, la prima differenza
    # non esiste e si perderebbe una settimana di serie.
    edges = [bounds[0][0] - timedelta(days=1)] + [u for _, u in bounds]
    cum = {e: _insights(account, token, anchor, e.isoformat(), "reach") for e in edges}
    wk = {u: _insights(account, token, s.isoformat(), u.isoformat(),
                       "impressions,spend,frequency,reach,actions") for s, u in bounds}

    series = {}
    for aid, info in meta.items():
        pts = []
        for i, (s, u) in enumerate(bounds):
            w = wk[u].get(aid)
            if not w:
                pts.append(None)          # adset spento quella settimana: buco, non zero
                continue
            imp = int(w.get("impressions", 0) or 0)
            spend = float(w.get("spend", 0) or 0)
            c_now = int((cum[u].get(aid) or {}).get("reach", 0) or 0)
            c_prev = int((cum[edges[i]].get(aid) or {}).get("reach", 0) or 0)
            new = max(c_now - c_prev, 0)
            res = _act(w, result_keys)
            pts.append({
                "week": u.isoformat(),
                "label": f"{s.strftime('%d/%m')}–{u.strftime('%d/%m')}",
                "new_people": new,
                "impressions": imp,
                "spend": round(spend, 2),
                "frequency": round(float(w.get("frequency", 0) or 0), 2),
                "results": res,
                "fti": round(100 * new / imp, 1) if imp else None,
                "cpr": round(spend / res, 2) if res else None,
                # Settimane dal lancio: serve alla vista "età dell'adset".
                "age": ((u - datetime.strptime(info["created"], "%Y-%m-%d").date()).days // 7
                        if info["created"] else None),
            })
        if any(p for p in pts):
            series[aid] = {**info, "points": pts,
                           # Storia troncata: l'adset esisteva prima dell'ancora, quindi
                           # il suo reach "dal lancio" qui non è davvero dal lancio.
                           "truncated": bool(info["created"] and info["created"] < anchor)}
    return {"account": account, "anchor": anchor,
            "weeks": [{"start": s.isoformat(), "end": u.isoformat(),
                       "label": f"{s.strftime('%d/%m')}–{u.strftime('%d/%m')}"} for s, u in bounds],
            "adsets": series}


if __name__ == "__main__":
    import os
    import sys
    tok = os.environ.get("META_TOKEN")
    if not tok:
        from store import get_meta_token
        tok = get_meta_token()
    acc = sys.argv[1] if len(sys.argv) > 1 else "act_1143079700337559"
    d = build(acc, tok)
    print(json.dumps(d, indent=2, ensure_ascii=False)[:3000])
