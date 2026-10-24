#!/usr/bin/env python3
# Variantu palyginimas: kuris balansavimas pasiekia >=26/30 per 60 kvietimu.
import json
import random
import time
from collections import Counter, deque

brain = json.load(open("/workspace/_smegenys_vp2.json", encoding="utf-8"))
ARR = [p for p in brain["frazes"]["phone"] if p.get("aktyvi", True) and p.get("tekstas")]


def k(p):
    return float(p.get("kartai") or 0)


def run(variant, n=60, ref="arr"):
    recent = deque(maxlen=8)
    last = [None]
    ids = []
    for i in range(n):
        pool = [p for p in ARR if str(p.get("id")) not in recent]
        if not pool:
            pool = list(ARR)
        if len(pool) > 1 and last[0] is not None:
            pool = [p for p in pool if str(p.get("id")) != str(last[0])] or pool
        base = ARR if ref == "arr" else pool
        mean = sum(k(p) for p in base) / max(1, len(base))
        med = sorted(k(p) for p in base)[len(base) // 2]
        rnd = random.Random("x:%d:%d" % (i, time.time_ns()))
        best, bv = None, -1.0
        for p in pool:
            a = max(0.01, float(p.get("a", 1)))
            b = max(0.01, float(p.get("b", 1)))
            kartai = k(p)
            q = a / (a + b)
            nov = 1.0 / (1.0 + kartai / 10.0)
            if variant == "spec":
                if mean > 0 and kartai > 2.0 * mean:
                    q *= 0.5
                s = 0.45 * q + 0.40 * rnd.random() + 0.15 * nov
            elif variant == "spec_med":
                if med > 0 and kartai > 2.0 * med:
                    q *= 0.5
                s = 0.45 * q + 0.40 * rnd.random() + 0.15 * nov
            elif variant == "spec_poolmean":
                if mean > 0 and kartai > 2.0 * mean:
                    q *= 0.5
                s = 0.45 * q + 0.40 * rnd.random() + 0.15 * nov
            elif variant == "med_taper":
                if med > 0 and kartai > med:
                    q *= max(0.5, med / kartai) if kartai <= 2.0 * med else 0.5
                s = 0.45 * q + 0.40 * rnd.random() + 0.15 * nov
            elif variant == "total_bal":
                if mean > 0 and kartai > 2.0 * mean:
                    q *= 0.5
                s = (0.45 * q + 0.40 * rnd.random() + 0.15 * nov) / (1.0 + kartai / max(1.0, mean))
            elif variant == "v4":
                s = 0.20 * q + 0.55 * rnd.random() + 0.25 * nov
            elif variant == "v5":
                s = 0.45 * (q ** 4) + 0.40 * rnd.random() + 0.15 * nov
            if s > bv:
                best, bv = p, s
        recent.append(str(best.get("id")))
        last[0] = str(best.get("id"))
        ids.append(best.get("id"))
    c = Counter(ids)
    consec = sum(1 for i in range(1, n) if ids[i] == ids[i - 1])
    return len(c), consec, c.most_common(3)


for variant in ("spec", "spec_med", "spec_poolmean", "med_taper", "total_bal", "v4", "v5"):
    res = []
    for t in range(3):
        res.append(run(variant, 60, "arr"))
    print("%-14s %s" % (variant, " | ".join("SK=%d/30 dupl=%d top=%s" % r for r in res)))
