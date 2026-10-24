#!/usr/bin/env python3
# Testas VPS: iskirpiam REALIAS auto-ciklo phone bloko eilutes is app.py ir paleidziam
# su stub emit_event + realiu _vp/_vp_names_lt + realia DB (read-only).
# Tikrinam: 1-as kvietimas -> "phone", 2-as/3-as -> "phone_catchup" su {"catchup": True} ir be {vardai}.
import ast
import json
import sqlite3
import sys
from collections import deque

SRC = "/opt/aukcionas/app.py"
DB = "/opt/aukcionas/aukcionas.db"
raw = open(SRC, encoding="utf-8").read()
lines = raw.split("\n")

A = next(i for i, l in enumerate(lines) if "# 3 skambu" in l and "KIEKVIENAS kitas seed" in l)
B = next(i for i, l in enumerate(lines) if l.strip() == '_VP_PHONE_ROUND["key"] = _ph_round')
print("Blokas app.py eil. %d..%d (%d eil.)" % (A + 1, B + 1, B - A + 1))
block = "\n".join((l[16:] if l.startswith(" " * 16) else l) for l in lines[A:B + 1])

text = raw
tree = ast.parse(text)
WANT = {"_VP_RECENT", "_VP_LAST", "_VP_PHONE_ROUND", "_vp", "_vp_names_lt",
        "VILKAS8_PHONE", "VILKAS8_PHONE_CORE", "VILKAS8_PHONE_EXTRA"}
parts = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in WANT for t in node.targets):
        parts.append(ast.get_source_segment(text, node))
    if isinstance(node, ast.FunctionDef) and node.name in WANT:
        parts.append(ast.get_source_segment(text, node))
print("AST dalys: %d (turi buti 8)" % len(parts))
if len(parts) != 8:
    sys.exit("STOP: neradau visu daliu")

brain = json.load(open("/opt/aukcionas/vilko_mokykla/smegenys.json", encoding="utf-8"))
ns = {"_vk_random": __import__("random"), "time": __import__("time"), "deque": deque,
      "vilko_brain": lambda: brain}
exec("\n".join(parts), ns)

code = ("def _tick(lot, _sa, use_elapsed, elapsed, quiet, remain, now, con, emit_event, _vp, "
        "_vp_names_lt, _VP_PHONE_ROUND, VILKAS8_PHONE):\n"
        + "\n".join(("    " + l) if l.strip() else l for l in block.split("\n")))
exec(code, ns)
_tick = ns["_tick"]
print("Bloko pirma eilute: %r" % block.split("\n")[0][:60])

con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
con.row_factory = sqlite3.Row
lot = con.execute("SELECT * FROM lots WHERE status='live' ORDER BY id DESC LIMIT 1").fetchone()
if not lot:
    lot = con.execute("SELECT * FROM lots ORDER BY id DESC LIMIT 1").fetchone()
lot = dict(lot)
print("Testuojama su lotu id=%s (%s)" % (lot["id"], str(lot.get("title"))[:40]))
nb = con.execute("SELECT COUNT(*) c FROM bids WHERE lot_id=?", (lot["id"],)).fetchone()["c"]
print("To loto statymu DB: %d" % nb)

calls = []


def emit_event(event_type, payload=None, priority=50, ttl=120, unique_key=None, con=None):
    calls.append({"type": event_type, "payload": payload, "uk": unique_key})
    return {"event_id": len(calls)}


_tick(lot, int(float(lot.get("starts_at") or 0)), True, 60.0, 60.0, 120.0, 999999.0, con,
      emit_event, ns["_vp"], ns["_vp_names_lt"], ns["_VP_PHONE_ROUND"], ns["VILKAS8_PHONE"])

print()
for c in calls:
    p = c["payload"]
    print("emit %s uk=%-22s n=%s phrase_id=%-18s catchup=%-5s | %s"
          % (c["type"], c["uk"], p.get("n"), p.get("phrase_id"), bool(p.get("catchup")),
             str(p.get("text"))[:70]))
print()
phone_n = sum(1 for c in calls if c["payload"].get("phrase_id") and
              not str(c["payload"]["phrase_id"]).startswith("phone_catchup"))
catch_n = sum(1 for c in calls if str(c["payload"].get("phrase_id") or "").startswith("phone_catchup"))
vardai = sum(1 for c in calls if "{vardai}" in str(c["payload"].get("text") or ""))
flags = sum(1 for c in calls if c["payload"].get("catchup") is True)
print("phone pool: %d | phone_catchup pool: %d | catchup:True: %d | liko {vardai}: %d"
      % (phone_n, catch_n, flags, vardai))
ok = (phone_n == 1 and catch_n == 2 and flags == 2 and vardai == 0)
print("REZULTATAS: %s" % ("OK - phone_catchup prijungtas ir {vardai} uzpildytas" if ok else "NEPAVYKO"))

# Antras ratas (kitas _sa) - vel turi buti "phone" pirmas
calls.clear()
_tick(lot, int(float(lot.get("starts_at") or 0)) + 1, True, 60.0, 60.0, 120.0, 999999.0, con,
      emit_event, ns["_vp"], ns["_vp_names_lt"], ns["_VP_PHONE_ROUND"], ns["VILKAS8_PHONE"])
print("Naujas ratas: phrase_id=%s catchup=%s (turi buti phone..., False)"
      % (calls[0]["payload"]["phrase_id"], bool(calls[0]["payload"].get("catchup"))))
con.close()
