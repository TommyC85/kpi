#!/usr/bin/env python3
"""Orchestratore LearnDash: costruisce la mappa persona→corsi e genera ld/index.html.
Env: LD_VARINI_URL/USER/PASS. Deploy della cartella ld/ su /tommaso/kpi/learndash/."""
import os

import build_ld_map
import ld_render

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    build_ld_map.main()          # fetch → ld_user_courses.json + ld_courses.json
    out = os.path.join(HERE, "ld")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(ld_render.build())
    with open(os.path.join(out, ".htaccess"), "w", encoding="utf-8") as f:
        f.write("DirectoryIndex index.html\nAddDefaultCharset UTF-8\n")
    print("ld/index.html generato")


if __name__ == "__main__":
    main()
