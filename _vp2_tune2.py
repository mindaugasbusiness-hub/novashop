#!/usr/bin/env python3
# Smulkus derinimas (10 bandymu): spec svoriai 0.45/0.40/0.15, suspausta kokybe/naujumas.
import json
import random
import time
from collections import Counter, deque

brain = json.load(open("/workspace/_smegenys_vp2.json", encoding="utf-8"))
ARR = [p for p in brain["frazes"]["phone"] if p.get("aktyvi", True) and p.get("tekstas")]


def k(p):
    return float(p.get("kartai") or 0)


MEAN = sum(k(p) for p in ARR) / len(ARR)


def run(comp_q, comp_n, n=60, trials=10, seed0=0):
    res = []
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
            rows = []
            for p in pool:
                a = max(0.01, float(p.get("a", 1)))
                b = max(0.01, float(p.get("b", 1)))
                q = a / (a + b)
                if MEAN > 0 and k(p) > 2.0 * MEAN:
                    q *= 0.5
                nov = 1.0 / (1.0 + k(p) / MEAN) if MEAN > 0 else 1.0
                rows.append((p, q, nov))
            qs = [r[1] for r in rows]
            ns = [r[2] for r in rows]
            qmin, qmax = min(qs), max(qs)
            nmin, nmax = min(ns), max(ns)
            rnd = random.Random("x:%d:%d:%d" % (seed0 + t, i, time.time_ns()))
            best, bv = None, -1.0
            for p, q, nov in rows:
                qrel = (q - qmin) / (qmax - qmin) if qmax > qmin else 0.5
                nrel = (nov - nmin) / (nmax - nmin) if nmax > nmin else 0.5
                s = (0.45 * (0.5 + comp_q * (qrel - 0.5))
                     + 0.40 * rnd.random()
                     + 0.15 * (0.5 + comp_n * (nrel - 0.5)))
                if s > bv:
                    best, bv = p, s
            recent.append(str(best.get("id")))
            last[0] = str(best.get("id"))
            ids.append(best.get("id"))
        res.append(len(set(ids)))
    return res


for comp_q, comp_n in ((0.02, 0.02), (0.02, 0.05), (0.03, 0.03), (0.05, 0.02), (0.05, 0.05), (0.08, 0.05), (0.10, 0.02)):
    r = run(comp_q, comp_n)
    print("comp_q=%.2f comp_n=%.2f -> %s min=%d vid=%.1f" % (comp_q, comp_n, r, min(r), sum(r) / len(r)))
