# KPI Dashboard — scorecard settimanale 4 clienti

Dashboard KPI per la valutazione del media buyer. Ogni lunedì, in automatico:
tira i dati (Meta + WooCommerce + Odoo) → genera una pagina e la carica su
`/tommaso/kpi/` (SiteGround, Basic Auth).

Per ogni cliente: un **North Star** (il numero che vale i soldi), i **KPI di
controllo** (attività diretta del media buyer, es. ad lanciate/settimana) e i
**KPI di risultato** (business). Il costo/appuntamento Pontoni è un *dato di
contesto* (grafico di andamento), non un obiettivo del media buyer.

## Come funziona

```
GitHub Actions (lun 06:46 UTC+2)
   └─ kpi_run.py
        ├─ kpi_engine.py   assembla i KPI (Meta + Woo + Odoo) + attività
        │     ├─ engine.py   pull insights Meta (riuso dal Riepilogo)
        │     ├─ woo.py      incasso reale WooCommerce (Varini)
        │     └─ odoo.py     funnel Pontoni — SOLA LETTURA (XML-RPC)
        └─ kpi_render.py   genera kpi/index.html (tema chiaro/scuro)
   └─ lftp                 carica kpi/ su SiteGround via FTPS
```

## File

| File | Ruolo |
|------|-------|
| `kpi_engine.py` | Assembla i KPI dei 4 clienti + target (ad lanciate, CPA…). **Modifica qui i target.** |
| `kpi_render.py` | Genera l'HTML della dashboard. |
| `kpi_run.py`    | Orchestratore. |
| `odoo.py`       | Connettore Odoo Pontoni, **sola lettura**. |
| `engine.py` / `woo.py` / `store.py` / `config.py` | Moduli condivisi (riuso dal Riepilogo). |
| `.github/workflows/weekly.yml` | Automazione settimanale + deploy. |

## Secrets richiesti (GitHub → Settings → Secrets → Actions)

`SUPABASE_URL`, `SUPABASE_KEY` (token Meta via OAuth), `WC_URL`, `WC_KEY`,
`WC_SECRET`, `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`,
`FTP_HOST`, `FTP_USER`, `FTP_PASS`, `FTP_DIR`.

## Uso locale

```bash
set -a; source secrets.env; set +a
python3 kpi_run.py            # settimana precedente a oggi
```
