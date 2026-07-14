#!/usr/bin/env python3
"""
Configurazione progetti per il Riepilogo Lunedì.

Ogni progetto definisce:
  - accounts : uno o più account Meta (act_...) da aggregare insieme
  - kpi      : "purchase" | "lead" — il risultato principale del progetto
  - aliases  : normalizzazione nome prodotto (chiave in minuscolo → nome pulito)
  - exclude  : sottostringhe di campaign_name da ignorare (es. campagne di test)

Il "prodotto" viene estratto dal nome campagna con la convenzione TMC:
  "TMC | <Prodotto> | <resto>"  oppure  "TMC | <Prodotto> - <data>"
Se serve raggruppare nomi diversi sullo stesso prodotto, usa `aliases`.
"""

# Nomi delle azioni Meta, in ordine di preferenza (si usa la prima presente).
ACTION_KEYS = {
    "purchase": ["offsite_conversion.fb_pixel_purchase", "purchase", "omni_purchase"],
    "lead":     ["lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"],
    "atc":      ["offsite_conversion.fb_pixel_add_to_cart", "add_to_cart", "omni_add_to_cart"],
}

PROJECTS = [
    {
        "name": "Balducci",
        "accounts": ["act_1083210079422366"],
        "kpi": "purchase",
        "aliases": {},
        "exclude": [],
    },
    {
        "name": "Varini",
        "accounts": ["act_2975289402775458"],
        "kpi": "purchase",
        # PUN e "Pentatonic Unlocked" sono lo stesso prodotto; Trim → TRIM.
        "aliases": {
            "pun": "Pentatonic Unlocked",
            "pentatonic unlocked": "Pentatonic Unlocked",
            "trim": "TRIM",
        },
        "exclude": [],
        # Incasso reale da WooCommerce (oltre ai tracciati Meta).
        "woo": True,
        # Obiettivo di profitto mensile (business totale). Profitto = incasso reale − spesa ADV − costi fissi.
        "monthly_profit_target": 20000,
        "monthly_fixed_costs": 0,   # ← eventuali costi fissi mensili da sottrarre
    },
    {
        "name": "Pontoni",
        "accounts": ["act_1143079700337559"],
        "kpi": "lead",
        # Tutte le varianti Nuance (città, offerta, ecc.) → un unico prodotto "Nuance".
        "aliases": {
            "nuance audio offerta": "Nuance",
            "occhialipersentire": "Nuance",
            "nuance": "Nuance",
        },
        "exclude": [],
    },
    {
        "name": "Di Domenico",
        # Allin + DDG (Studio GD): due account, stesso referente.
        "accounts": ["act_3097227940528224", "act_1048267528538993"],
        "kpi": "purchase",
        "aliases": {},
        "exclude": [],
    },
]
