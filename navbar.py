#!/usr/bin/env python3
"""Barra di navigazione condivisa con menu a tendina (raggruppata per area).
Usata da kpi_render / pontoni_render / ld_render / riacquisti_render.
Le pagine del repo Riepilogo (dashboard, varini) replicano la stessa struttura a mano."""

# Struttura menu: (Gruppo, [(voce, url), ...])
MENU = [
    ("Riepilogo", [("Generale", "/tommaso/"), ("KPI clienti", "/tommaso/kpi/")]),
    ("Varini", [("Gestione clienti", "/tommaso/varini/"),
                ("Corsi", "/tommaso/kpi/learndash/"),
                ("Riacquisti", "/tommaso/kpi/riacquisti/")]),
    ("Pontoni", [("Spaccato moduli", "/tommaso/kpi/pontoni/")]),
]

# CSS per pagine con token stile KPI (--panel/--panel-2/--line/--ink/--ink-2/--accent/--accent-soft)
NAV_CSS = """
.topnav{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 14px;margin-bottom:22px;box-shadow:var(--shadow)}
.topnav .brand{font-weight:750;font-size:13.5px}
.menu{list-style:none;display:flex;gap:2px;margin:0;padding:0;flex-wrap:wrap}
.menu .grp{position:relative}
.menu .top{display:block;font-size:13px;font-weight:600;color:var(--ink-2);padding:6px 12px;border-radius:8px;white-space:nowrap;cursor:pointer;background:none;border:0;font-family:inherit}
.menu .grp:hover .top,.menu .grp:focus-within .top{background:var(--panel-2);color:var(--ink)}
.menu .grp.active .top{background:var(--accent-soft);color:var(--accent)}
.menu .sub{list-style:none;margin:0;padding:6px;position:absolute;left:0;top:100%;min-width:190px;background:var(--panel);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);display:none;z-index:40}
.menu .grp:hover .sub,.menu .grp:focus-within .sub{display:block}
.menu .sub a{display:block;font-size:13px;color:var(--ink-2);text-decoration:none;padding:7px 12px;border-radius:7px;white-space:nowrap}
.menu .sub a:hover{background:var(--panel-2);color:var(--ink)}
.menu .sub a.active{color:var(--accent);font-weight:700}
"""


def nav_html(current: str) -> str:
    """current = url della pagina attuale (es. '/tommaso/kpi/pontoni/')."""
    groups = ""
    for name, items in MENU:
        active = any(url == current for _, url in items)
        subs = "".join(
            f'<li><a href="{url}"{" class=\"active\"" if url == current else ""}>{label}</a></li>'
            for label, url in items)
        groups += (f'<li class="grp{" active" if active else ""}">'
                   f'<button class="top" tabindex="0">{name} ▾</button>'
                   f'<ul class="sub">{subs}</ul></li>')
    return ('<nav class="topnav"><span class="brand">📊 Media Buying</span>'
            f'<ul class="menu">{groups}</ul></nav>')
