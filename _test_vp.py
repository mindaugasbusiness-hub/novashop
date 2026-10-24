#!/usr/bin/env python3
# Simuliacinis testas _vp(): funkcija iskirpta AST budu is REALIAI ikelto app.py
# (/workspace/_app_after_vp.py == VPS /opt/aukcionas/app.py) ir paleidziama
# su tikru smegenys.json (kopija /workspace/_smegenys_vp.json).
# Nenaudojamas app.py importas (kad nebutu salytiniu poveikiu).
import ast
import json
import os
import random
import time
from collections import Counter, deque

SRC = os.environ.get("VP_SRC", "/workspace/_app_after_vp.py")
BRAIN = os.environ.get("VP_BRAIN", "/workspace/_smegenys_vp.json")

text = open(SRC, encoding="utf-8").read()
tree = ast.parse(text)

parts = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) in ("_VP_RECENT", "_VP_LAST") for t in node.targets):
        parts.append(ast.get_source_segment(text, node))
    if isinstance(node, ast.FunctionDef) and node.name == "_vp":
        parts.append(ast.get_source_segment(text, node))
print("Is app.py iskirptos dalys: %d (turi buti 3)" % len(parts))
if len(parts) != 3:
    raise SystemExit("STOP: neradau _VP_RECENT/_VP_LAST/_vp")

brain = json.load(open(BRAIN, encoding="utf-8"))
ns = {"_vk_random": random, "time": time, "deque": deque, "vilko_brain": lambda: brain}
exec("\n".join(parts), ns)
_vp = ns["_vp"]


def old_vp(kind, seed, fixed_ts):
    """SENAS algoritmas (pries pataisa) — palyginimui, ta pati 15 min sekla."""
    arr = [p for p in brain["frazes"].get(kind, []) if p.get("aktyvi", True) and p.get("tekstas")]
    if not arr:
        return None
    rnd = random.Random("%s:%s:%d" % (kind, seed, int(fixed_ts // 900)))
    best, bv = None, -1.0
    for p in arr:
        v = rnd.betavariate(max(0.01, float(p.get("a", 1))), max(0.01, float(p.get("b", 1))))
        if v > bv:
            best, bv = p, v
    return best["id"]


def run_new(kind, n, fallback):
    ids, txt = [], []
    for i in range(n):
        r = _vp(kind, 1000 + i * 7, fallback)
        ids.append(r["phrase_id"])
        txt.append(r["text"])
        time.sleep(0.001)
    return ids, txt


def report(kind, ids, n):
    c = Counter(ids)
    consec = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
    top3 = c.most_common(3)
    print("%-6s | kvietimu=%d | SKIRTINGU=%d/%d | 2-is-eiles-vienodu=%d | top3=%s"
          % (kind, n, len(c), n, consec, [(k, v) for k, v in top3]))
    return len(c), consec


print("--- NAUJAS _vp (po pataisos) ---")
ids_p, txt_p = run_new("phone", 30, ["Alio, alio!"])
report("phone", ids_p, 30)
ids_j, txt_j = run_new("joke", 10, ["Bajeriukas!"])
report("joke", ids_j, 10)
ids_n, txt_n = run_new("nudge", 10, ["Kas kitas?"])
report("nudge", ids_n, 10)

print("--- SENAS algoritmas (pries pataisa), tie patys 30 'phone' kvietimu ---")
fixed = time.time()
old_ids = [old_vp("phone", 1000 + i * 7, fixed) for i in range(30)]
oc = Counter(old_ids)
print("phone | SKIRTINGU=%d/30 | 2-is-eiles-vienodu=%d | top3=%s"
      % (len(oc), sum(1 for i in range(1, 30) if old_ids[i] == old_ids[i - 1]), oc.most_common(3)))
old_900 = [old_vp("phone", 1000, fixed) for _ in range(30)]
print("phone (tas pats seed 30x per 15 min) | SKIRTINGU=%d/30" % len(set(old_900)))

print("--- NAUJO teksto pavyzdys (phone, pirmi 10) ---")
for i, (pid, t) in enumerate(zip(ids_p[:10], txt_p[:10]), 1):
    print("%2d. %s | %s" % (i, pid, t[:70]))
