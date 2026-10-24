#!/usr/bin/env python3
# Lokali simuliacija: KAIP atrodys naujas _vp() (0.45/0.40/0.15 + kartu balansavimas).
# Tikslas: 60 kvietimu -> >=26 skirtingu is 30. Bandome pries keisdami serveri.
import json
import random
import time
from collections import Counter, deque

BRAIN = "/workspace/_smegenys_vp2.json"
brain = json.load(open(BRAIN, encoding="utf-8"))

_VP_RECENT = {}
_VP_LAST = {}


def _vp(kind, seed, fallback_list):
    try:
        arr = [p for p in (brain.get("frazes") or {}).get(kind, [])
               if p.get("aktyvi", True) and p.get("tekstas")]
    except Exception:
        arr = []
    if not arr:
        fl = list(fallback_list or [""])
        return {"text": fl[int(seed) % len(fl)], "phrase_id": None}
    recent = _VP_RECENT.setdefault(kind, deque(maxlen=8))
    pool = [p for p in arr if str(p.get("id")) not in recent]
    if not pool:
        pool = list(arr)
    last = _VP_LAST.get(kind)
    if len(pool) > 1 and last is not None:
        pool = [p for p in pool if str(p.get("id")) != str(last)] or pool

    def _kartai(p):
        try:
            return float(p.get("kartai") or 0)
        except Exception:
            return 0.0

    mean_kartai = (sum(_kartai(p) for p in arr) / len(arr)) if arr else 0.0
    rnd = random.Random(f"{kind}:{seed}:{time.time_ns()}")
    best, bv = None, -1.0
    for p in pool:
        a = max(0.01, float(p.get("a", 1)))
        b = max(0.01, float(p.get("b", 1)))
        kartai = _kartai(p)
        quality = a / (a + b)
        if mean_kartai > 0 and kartai > 2.0 * mean_kartai:
            quality *= 0.5
        score = 0.45 * quality + 0.40 * rnd.random() + 0.15 * (1.0 / (1.0 + kartai / 10.0))
        if score > bv:
            best, bv = p, score
    chosen = str(best.get("id"))
    recent.append(chosen)
    _VP_LAST[kind] = chosen
    return {"text": best["tekstas"], "phrase_id": best.get("id")}


def run(kind, n, fallback, sleep=0.001):
    ids = []
    for i in range(n):
        r = _vp(kind, 1000 + i * 7, fallback)
        ids.append(r["phrase_id"])
        time.sleep(sleep)
    return ids


for trial in range(3):
    _VP_RECENT.clear()
    _VP_LAST.clear()
    ids = run("phone", 60, ["Alio, alio!"])
    c = Counter(ids)
    consec = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
    print("bandymas %d: SKIRTINGU=%d/30 | 2-is-eiles-vienodu=%d | top3=%s"
          % (trial + 1, len(c), consec, c.most_common(3)))
    print("   neradusios: %s" % sorted(set(p["id"] for p in brain["frazes"]["phone"]) - set(ids)))

_VP_RECENT.clear()
_VP_LAST.clear()
for kind, n in (("joke", 10), ("nudge", 10), ("phone_catchup", 12)):
    ids = run(kind, n, ["x"])
    c = Counter(ids)
    print("%-14s kvietimu=%d SKIRTINGU=%d/%d top3=%s"
          % (kind, n, len(c), n, c.most_common(3)))
