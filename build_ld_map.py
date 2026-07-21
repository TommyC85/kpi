#!/usr/bin/env python3
"""Costruisce la mappa persona→corsi da LearnDash (Varini) e la salva in ld_user_courses.json.
Con retry + checkpoint per corso. Env: LD_VARINI_URL/USER/PASS."""
import os, requests, certifi, base64, json, time, re
from collections import Counter, defaultdict

url = os.environ["LD_VARINI_URL"].rstrip("/")
usr = os.environ["LD_VARINI_USER"]; pw = os.environ["LD_VARINI_PASS"]
H = {"Authorization": "Basic " + base64.b64encode(f"{usr}:{pw}".encode()).decode()}
S = requests.Session(); S.headers.update(H); S.verify = certifi.where()
HERE = os.path.dirname(os.path.abspath(__file__))


def get(path, **p):
    for attempt in range(5):
        try:
            return S.get(url + path, params=p, timeout=45)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))


def log(m):
    with open(os.path.join(HERE, "ld_build_status.txt"), "a") as f:
        f.write(m + "\n")
    print(m, flush=True)


MAP_F = os.path.join(HERE, "ld_user_courses.json")
DONE_F = os.path.join(HERE, "ld_done_courses.json")


def _save(uc, done):
    json.dump({str(u): sorted(int(c) for c in v) for u, v in uc.items()}, open(MAP_F, "w"))
    json.dump(sorted(done), open(DONE_F, "w"))


def main():
    courses = {}; page = 1
    while True:
        d = get("/wp-json/ldlms/v2/sfwd-courses", per_page=100, page=page, _fields="id,title").json()
        if not d:
            break
        for c in d:
            t = c.get("title"); courses[c["id"]] = (t.get("rendered") if isinstance(t, dict) else t) or str(c["id"])
        if len(d) < 100:
            break
        page += 1
    json.dump(courses, open(os.path.join(HERE, "ld_courses.json"), "w"), ensure_ascii=False)

    # RESUME: ricarica mappa + corsi già fatti
    uc = defaultdict(set)
    if os.path.isfile(MAP_F):
        for u, cs in json.load(open(MAP_F)).items():
            uc[int(u)] = set(cs)
    done = set(json.load(open(DONE_F))) if os.path.isfile(DONE_F) else set()
    # seed: i corsi già presenti nella mappa parziale sono di fatto già processati
    done |= {c for cs in uc.values() for c in cs}
    todo = [c for c in courses if c not in done]
    log(f"corsi: {len(courses)} | già fatti: {len(done)} | da fare: {len(todo)} | utenti finora: {len(uc)}")

    for i, cid in enumerate(todo, 1):
        page = 1
        while True:
            r = get(f"/wp-json/ldlms/v2/sfwd-courses/{cid}/users", per_page=100, page=page, _fields="id")
            if r.status_code != 200:
                break
            d = r.json()
            if not d:
                break
            for u in d:
                uc[u["id"]].add(cid)
            if len(d) < 100:
                break
            page += 1
        done.add(cid)
        if i % 5 == 0:
            log(f"  ...{len(done)}/{len(courses)} corsi · {len(uc)} utenti")
            _save(uc, done)
    _save(uc, done)
    nc = Counter(len(v) for v in uc.values())
    one = [u for u, v in uc.items() if len(v) == 1]
    sbc = Counter(next(iter(uc[u])) for u in one)
    log(f"FATTO. utenti con >=1 corso: {len(uc)} | con 1 solo corso: {len(one)}")
    log("distribuzione nr corsi/persona: " + json.dumps({k: nc[k] for k in sorted(nc)}))
    log("TOP corsi tra chi ne ha 1 solo:")
    for cid, n in sbc.most_common(15):
        log(f"   {n:>5}  " + re.sub(r'&#?\w+;', ' ', courses.get(cid, str(cid))))


if __name__ == "__main__":
    main()
