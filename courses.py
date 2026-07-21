#!/usr/bin/env python3
"""Normalizzazione nomi corsi Varini → linea di corso canonica.
Varini usa sia nomi estesi sia SIGLE (EGS, AGS, CHAC, CHEL, TRIM, GHC, PUN, PEPO, FIBA, BBASE...).
Le sigle si matchano come PAROLA INTERA (evita falsi positivi tipo 'ega' dentro 'legato')."""
import re

# Nomi ESTESI → linea (match per sottostringa, sicuri perché lunghi). Ordine: specifico prima.
FULL = [
    ("electric guitar booster", "Electric Guitar Booster"),
    ("acoustic guitar booster", "Acoustic Guitar Booster"),
    ("electric guitar starter", "Electric Guitar Starter"),
    ("acoustic guitar starter", "Acoustic Guitar Starter"),
    ("classic guitar starter", "Classic Guitar Starter"),
    ("classical guitar starter", "Classic Guitar Starter"),
    ("the rhythm is magic", "The Rhythm Is Magic"),
    ("guitar hacking", "Guitar Hacking Challenge"),
    ("pentatonic unlocked", "Pentatonic Unlocked"),
    ("pentatonic pack", "Pentatonic Unlocked"),
    ("pentatonic power", "Pentatonic Power"),
    ("fingerpicking base", "Fingerpicking Base"),
    ("blues base", "Blues Base"), ("blues intermedio", "Blues Intermedio"),
    ("blues avanzato", "Blues Avanzato"), ("blues pro", "Blues Pro"),
    ("arpeggio master", "Arpeggio Master"), ("jazz survival", "Jazz Survival"),
    ("pentatonic power", "Pentatonic Power"),
    ("suonare gli intervalli", "Suonare Gli Intervalli"),
    ("theory made easy", "Theory Made Easy"),
    ("guitar setup", "Guitar Setup"), ("super simple setup", "Guitar Setup"),
    ("guitar sound", "Bonus (Sound/Tuning)"), ("guitar tuning", "Bonus (Sound/Tuning)"),
    ("rock one", "Rock One"), ("rock two", "Rock Two"),
]

# SIGLE → linea (match parola intera). ⚠️ DA VALIDARE con Varini.
ACR = {
    "egs": "Electric Guitar Starter", "ega": "Electric Guitar Starter",
    "chel1": "Electric Guitar Starter", "chel2": "Electric Guitar Starter", "chel3": "Electric Guitar Starter",
    "chel_int1": "Electric Guitar Booster", "chel_int2": "Electric Guitar Booster",
    "ags": "Acoustic Guitar Starter",
    "chac1": "Acoustic Guitar Starter", "chac2": "Acoustic Guitar Starter", "chac3": "Acoustic Guitar Starter",
    "chac_int1": "Acoustic Guitar Booster", "chac_int2": "Acoustic Guitar Booster",
    "chcl": "Classic Guitar Starter",
    "trim": "The Rhythm Is Magic", "ghc": "Guitar Hacking Challenge",
    "pun": "Pentatonic Unlocked", "pepo": "Pentatonic Power",
    "fiba": "Fingerpicking Base",
    "bbase": "Blues Base", "blint": "Blues Intermedio", "blav": "Blues Avanzato", "bpro": "Blues Pro",
    "ama": "Arpeggio Master",
}

# Non-corso: prodotti-ponte / prova / bonus da escludere dalle analisi corso.
EXCLUDE_CANON = {"Bonus (Sound/Tuning)"}
EXCLUDE_KW = ("community", "try before", "try before you buy",
              # bonus/omaggio dati a tappeto (non vendite) — confermati da Varini
              "guitar mindset", "theory made easy", "healthy performer", "sounds of guitar")


def _norm(name):
    return re.sub(r"&#?\w+;", " ", (name or "").lower())


def is_excluded(name):
    n = _norm(name)
    return any(x in n for x in EXCLUDE_KW)


def canon(name):
    n = _norm(name)
    for kw, c in FULL:
        if kw in n:
            return c
    for a, c in ACR.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", n):
            return c
    return re.sub(r"\s+", " ", re.sub(r"\[.*?\]|\(.*?\)", "", name or "")).strip()
