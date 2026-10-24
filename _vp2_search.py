#!/usr/bin/env python3
# Paieska: kokia formule duoda >=26/30 per 60 kvietimu (5 bandymai).
import json
import random
import time
from collections import Counter, deque

brain = json.load(open("/workspace/_smegenys_vp2.json", encoding="utf-8"))
ARR = [p for p in brain["frazes"]["phone"] if p.get("aktyvi", True) and p.get("tekstas")]


def k(p):
    return float(p.get("kartai") or 0)


MEAN = sum(k(p) for p in ARR) / len(ARR)
MED = sorted(k(p) for p in ARR)[len(ARR) // 2]


def run(cfg, n=60, trials=5):
    qw, rw, nw, comp, nov, hard = cfg
    res = []
    for t in range(trials):
        recent = deque(maxlen=8)
        last = [None]
        ids = []
        for i in range(n):
            pool = [p for p in ARR if str(p.get("id")) not in recent]
            if not pool:
                pool = list(ARR)
            if hard:
                h = [p for p in pool if not (MEAN > 0 and k(p) > 2.0 * MEAN)]
                if h:
                    pool = h
            if len(pool) > 1 and last[0] is not None:
                pool = [p for p in pool if str(p.get("id")) != str(last[0])] or pool
            qs = []
            for p in pool:
                a = max(0.01, float(p.get("a", 1)))
                b = max(0.01, float(p.get("b", 1)))
                q = a / (a + b)
                if MEAN > 0 and k(p) > 2.0 * MEAN:
                    q *= 0.5
                qs.append(q)
            qmin, qmax = min(qs), max(qs)
            rnd = random.Random("x:%d:%d" % (i, time.time_ns()))
            best, bv = None, -1.0
            for p, q in zip(pool, qs):
                kartai = k(p)
                qrel = (q - qmin) / (qmax - qmin) if qmax > qmin else 0.5
                qterm = 0.5 + comp * (qrel - 0.5)
                if nov == "rel":
                    nterm = 1.0 / (1.0 + kartai / MEAN) if MEAN > 0 else 1.0
                else:
                    nterm = 1.0 / (1.0 + kartai / 10.0)
                s = qw * qterm + rw * rnd.random() + nw * nterm
                if s > bv:
                    best, bv = p, s
            recent.append(str(best.get("id")))
            last[0] = str(best.get("id"))
            ids.append(best.get("id"))
        c = Counter(ids)
        res.append(len(c))
    return res


print("MEAN=%.1f MED=%.1f" % (MEAN, MED))
print("T1 uniform per pool: %s" % run((0.0, 1.0, 0.0, 0.0, "abs", False)))
print("T1b uniform + hard>2mean: %s" % run((0.0, 1.0, 0.0, 0.0, "abs", True)))

CANDS = []
for comp in (0.10, 0.20, 0.30):
    for nov in ("abs", "rel"):
        for qw, rw, nw in ((0.45, 0.40, 0.15), (0.30, 0.55, 0.15), (0.15, 0.70, 0.15), (0.10, 0.75, 0.15)):
            CANDS.append((qw, rw, nw, comp, nov, True))

best = None
for cfg in CANDS:
    r = run(cfg, 60, 3)
    tag = "q=%.2f r=%.2f n=%.2f comp=%.2f nov=%s" % cfg[:5]
    print("%-42s -> %s  (min=%d)" % (tag, r, min(r)))
    if min(r) >= 26 and (best is None or min(r) > best[1]):
        best = (cfg, min(r))
print("GERIAUSIA: %s" % (best,))
