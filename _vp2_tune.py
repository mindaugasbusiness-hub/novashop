#!/usr/bin/env python3
# Tikslus derinimas: kiek svoriu reikia, kad 60 kvietimu duotu >=26/30 stabiliai (8 bandymai).
import json
import random
import time
from collections import Counter, deque

brain = json.load(open("/workspace/_smegenys_vp2.json", encoding="utf-8"))
ARR = [p for p in brain["frazes"]["phone"] if p.get("aktyvi", True) and p.get("tekstas")]


def k(p):
    return float(p.get("kartai") or 0)


MEAN = sum(k(p) for p in ARR) / len(ARR)


def run(cfg, n=60, trials=8):
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
                nterm = (1.0 / (1.0 + kartai / MEAN)) if nov == "rel" else (1.0 / (1.0 + kartai / 10.0))
                s = qw * qterm + rw * rnd.random() + nw * nterm
                if s > bv:
                    best, bv = p, s
            recent.append(str(best.get("id")))
            last[0] = str(best.get("id"))
            ids.append(best.get("id"))
        res.append(len(set(ids)))
    return res


TESTS = [
    ("A q.05 r.90 n.05 comp.05 abs", (0.05, 0.90, 0.05, 0.05, "abs", False)),
    ("B q.10 r.85 n.05 comp.05 abs", (0.10, 0.85, 0.05, 0.05, "abs", False)),
    ("C q.05 r.85 n.10 comp.05 rel", (0.05, 0.85, 0.10, 0.05, "rel", False)),
    ("D q.00 r.90 n.10 comp.00 abs", (0.00, 0.90, 0.10, 0.00, "abs", False)),
    ("E uniform (ref)", (0.0, 1.0, 0.0, 0.0, "abs", False)),
    ("F A + hard>2mean", (0.05, 0.90, 0.05, 0.05, "abs", True)),
    ("G q.10 r.80 n.10 comp.05 abs", (0.10, 0.80, 0.10, 0.05, "abs", False)),
    ("H q.05 r.90 n.05 comp.05 rel", (0.05, 0.90, 0.05, 0.05, "rel", False)),
]
for label, cfg in TESTS:
    r = run(cfg)
    print("%-32s -> %s  min=%d vid=%.1f" % (label, r, min(r), sum(r) / len(r)))
