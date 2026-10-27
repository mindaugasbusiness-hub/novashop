#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATRAKINA sokejos rotacija (M prasymas 2026-10-27).

Kas keiciama:
  - get_dancer_public()  ir  dancer_next_public()  grazinami i ORIGINALIA logika
    (auto-rotacija kas DANCER_ROTATE_S, F5/F10 -> kita sokeja).
  - NELIEciama: DESK_SONG_TITLES, CSS, mazoji neonine plytele.

Mazoji plytele kairiajame kampe turi savo <video class="nd-video" src="/photos/dance_club_12.mp4">
ir JS rotacija (kuri dirba su .dd-video) jos neliecia — todel ji liks #12.

Naudojimas serveryje:
  python3 /tmp/unlock_dancer.py            # tikrina
  python3 /tmp/unlock_dancer.py --write    # iraso (su .bak kopija)
"""
import ast
import datetime
import os
import shutil
import sys

LIVE = "/opt/aukcionas/app.py"
START = "def get_dancer_public():"
STOP = "DESK_SONG_TITLES = {"

ORIGINAL = '''def get_dancer_public():
    """Dabartine sokeja visiems. Auto-rotacija pagal laika, be localStorage skirtumu."""
    now = time.time()
    total = len(DANCER_URLS)
    idx, at = _dancer_read_state()
    if at <= 0:
        at = now
    idx = idx % total
    steps = int((now - at) // DANCER_ROTATE_S) if now >= at else 0
    if steps > 0:
        idx = (idx + steps) % total
        at = at + steps * DANCER_ROTATE_S
        _dancer_write_state(idx, at)
    elif at > now:
        _dancer_write_state(idx, now)
        at = now
    url = DANCER_URLS[idx % total]
    return {"url": url, "n": (idx % total) + 1, "total": total, "idx": idx % total}


def dancer_next_public():
    now = time.time()
    total = len(DANCER_URLS)
    idx, at = _dancer_read_state()
    if now - float(at or 0) < DANCER_NEXT_MIN_S:
        return get_dancer_public()
    idx = (int(idx) + 1) % total
    _dancer_write_state(idx, now)
    url = DANCER_URLS[idx]
    return {"url": url, "n": idx + 1, "total": total, "idx": idx}
'''

MARK = '"""Dabartine sokeja visiems.'


def main():
    write = "--write" in sys.argv[1:]
    src = open(LIVE, "r", encoding="utf-8", newline="").read()

    if MARK in src:
        print("JAU ATRAKINTA (rotacija yra). NIEKO NEDARAU.")
        return 0

    i = src.find(START)
    j = src.find(STOP)
    if i < 0 or j < 0 or j < i:
        print("STOP: neradau ribu (START=%d, STOP=%d)" % (i, j))
        return 2
    old = src[i:j]
    print("keiciamas blokas: %d B, %d eil." % (len(old), old.count("\n") + 1))

    nl = "\r\n" if "\r\n" in src else "\n"
    new_block = ORIGINAL.replace("\n", nl) + nl + nl
    out = src[:i] + new_block + src[j:]

    try:
        ast.parse(out)
        print("sintakse po pakeitimo: OK")
    except SyntaxError as exc:
        print("STOP: sintakses klaida: %s" % exc)
        return 3

    print("butu: %d -> %d B (%+d)" % (len(src), len(out), len(out) - len(src)))
    if not write:
        print("DRY-RUN. Irasymui: --write")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-unlock-%s" % (LIVE, stamp)
    shutil.copyfile(LIVE, bak)
    with open(LIVE, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("IRASYTA. Kopija: %s" % bak)
    print("Kitas zingsnis: systemctl restart aukcionas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
