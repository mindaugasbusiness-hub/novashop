import json
import sqlite3
import time

c = sqlite3.connect("/opt/aukcionas/aukcionas.db")
c.row_factory = sqlite3.Row
print("=== Paskutiniai 12 ivykiu (visi tipai) ===")
for x in c.execute("SELECT event_id,event_type,unique_key,payload,created_at FROM events ORDER BY event_id DESC LIMIT 12"):
    try:
        d = json.loads(x["payload"])
    except Exception:
        d = {}
    print("%6s %-10s %-28s %s | %s" % (x["event_id"], x["event_type"], str(x["unique_key"])[:28],
                                       time.strftime("%H:%M:%S", time.localtime(x["created_at"])),
                                       str(d.get("text") or d.get("phrase_id") or "")[:46]))
print("dabar:", time.strftime("%H:%M:%S"))
print()
print("=== Bids paskutinis (ar botai stato) ===")
for x in c.execute("SELECT id,lot_id,name,amount,at FROM bids ORDER BY id DESC LIMIT 5"):
    print("bid %s lot=%s %s %.0f %s" % (x["id"], x["lot_id"], x["name"], x["amount"],
                                        time.strftime("%H:%M:%S", time.localtime(x["at"]))))
print()
print("=== lots statusu suvestine ===")
for x in c.execute("SELECT status, COUNT(*) n, MAX(id) mx FROM lots GROUP BY status"):
    print("%-8s %d (max id %s)" % (x["status"], x["n"], x["mx"]))
