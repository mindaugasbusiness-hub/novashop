import json
import sqlite3
import time

DB = "/opt/aukcionas/aukcionas.db"
seen = set()
hits = []
end = time.time() + 300
while time.time() < end:
    try:
        con = sqlite3.connect(DB)
        rows = con.execute(
            "SELECT event_id,payload,datetime(created_at,'unixepoch','localtime') t,unique_key "
            "FROM events WHERE event_type='phone' AND event_id > "
            "(SELECT COALESCE(MAX(event_id),0)-400 FROM events) ORDER BY event_id ASC"
        ).fetchall()
        lot = con.execute("SELECT id,status,title,datetime(starts_at,'unixepoch','localtime') FROM lots "
                          "WHERE status='live' ORDER BY id DESC LIMIT 1").fetchone()
        con.close()
        for eid, p, t, uk in rows:
            if eid in seen:
                continue
            seen.add(eid)
            try:
                d = json.loads(p)
            except Exception:
                continue
            if d.get("manual"):
                continue
            line = "AUTO %s eid=%s uk=%s n=%s phrase=%s catchup=%s | %s" % (
                t, eid, uk, d.get("n"), d.get("phrase_id"), bool(d.get("catchup")),
                str(d.get("text"))[:70])
            print(line, flush=True)
            if d.get("catchup"):
                hits.append(line)
        if lot:
            print("live lot: %s %s (%s)" % (lot[0], lot[1], lot[3]), flush=True)
    except Exception as e:
        print("klaida:", type(e).__name__, e, flush=True)
    time.sleep(15)
print("CATCHUP IVYKIU: %d" % len(hits), flush=True)
for h in hits:
    print(h, flush=True)
