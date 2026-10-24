#!/usr/bin/env python3
# Tinklelis: (kokybes svoris, atsitiktinumo svoris, naujumo svoris) su normalizuota kokybe
# ir santykiniu naujumu (kartai/mean). Ieskome konfiguracijos, kuri duoda >=26/30.
import json
import random
import time
from collections import Counter, deque

brain = json.load(open("/workspace/_smegenys_vp2.json", encoding="utf-8"))
ARR = [p for p in brain["frazes"]["phone"] if p.get("aktyvi", True) and p.get("tekstas")]


def k(p):
    return float(p.get("kartai") or 0)


def run(qw, rw, nw, norm_q, nov_rel, n=60, trials=3):
    out = []
    for t in range(trials):
        recent = deque(maxlen=8)
        last = [None]
        ids = []
        for i in range(n):
            pool = [p for p in ARR if str(p.get("id")) not in recent]
            if not pool:
                pool = list(ARR)
            if len(pool) > 1 and last[0] is not None:
                pool = [p for p in pool if str(p.get("id")) != str(last[0])] or pool
            mean = sum(k(p) for p in ARR) / max(1, len(ARR))
            qs = []
            for p in pool:
                a = max(0.01, float(p.get("a", 1)))
                b = max(0.01, float(p.get("b", 1)))
                q = a / (a + b)
                if mean > 0 and k(p) > 2.0 * mean:
                    q *= 0.5
                qs.append(q)
            qmin, qmax = min(qs), max(qs)
            rnd = random.Random("x:%d:%d" % (i, time.time_ns()))
            best, bv = None, -1.0
            for p, q in zip(pool, qs):
                kartai = k(p)
                if norm_q:
                    qq = (q - qmin) / (qmax - qmin) if qmax > qmin else 0.5
                else:
                    qq = q
                nov = 1.0 / (1.0 + kartai / mean) if (nov_rel and mean > 0) else 1.0 / (1.0 + kartai / 10.0)
                s = qw * qq + rw * rnd.random() + nw * nov
                if s > bv:
                    best, bv = p, s
            recent.append(str(best.get("id")))
            last[0] = str(best.get("id"))
            ids.append(best.get("id"))
        c = Counter(ids)
        consec = sum(1 for i in range(1, n) if ids[i] == ids[i - 1])
        out.append((len(c), consec, c.most_common(3)))
    return out


CFG = [
    (0.10, 0.60, 0.30, True, True),
    (0.15, 0.50, 0.35, True, True),
    (0.05, 0.55, 0.40, True, True),
    (0.25, 0.45, 0.30, True, True),
    (0.10, 0.70, 0.20, True, True),
    (0.00, 0.70, 0.30, True, True),
    (0.10, 0.50, 0.40, True, True),
    (0.05, 0.70, 0.25, True, True),
    (0.15, 0.40, 0.45, True, True),
]
for cfg in CFG:
    res = run(*cfg)
    print("q=%.2f r=%.2f n=%.2f norm=%s rel=%s -> %s"
          % (cfg[0], cfg[1], cfg[2], cfg[3], cfg[4],
             " | ".join("SK=%d/30 dupl=%d top=%s" % r for r in res)))
