#!/usr/bin/env python3
# VPS: /tmp/vp_events.py — tik REALUS (ne F11) phone ivykiai is events lenteles.
import json
import sqlite3

con = sqlite3.connect("/opt/aukcionas/aukcionas.db")
rows = con.execute(
    "SELECT event_id, payload, datetime(created_at,'unixepoch','localtime') FROM events "
    "WHERE event_type='phone' ORDER BY event_id DESC LIMIT 80"
).fetchall()
con.close()

seq = []
for eid, p, t in reversed(rows):
    try:
        d = json.loads(p)
    except Exception:
        continue
    if d.get("manual"):
        continue
    seq.append(d.get("phrase_id"))
    print("%5s %s n=%s phrase_id=%-10s | %s" % (eid, t, d.get("n"), d.get("phrase_id"), str(d.get("text"))[:58]))

print("---")
if seq:
    print("REALUS phone ivykiai: %d | SKIRTINGU phrase_id: %d | 2-is-eiles-vienodu: %d"
          % (len(seq), len(set(seq)), sum(1 for i in range(1, len(seq)) if seq[i] == seq[i - 1])))
else:
    print("REALIU phone ivykiu nera")
