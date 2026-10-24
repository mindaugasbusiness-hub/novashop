import sqlite3
import time

c = sqlite3.connect("/opt/aukcionas/aukcionas.db")
c.row_factory = sqlite3.Row
for x in c.execute("SELECT id,status,ends_at,starts_at FROM lots WHERE status='live'"):
    print("live lot %s | start %s | end %s | liko s: %d"
          % (x["id"], time.strftime("%H:%M:%S", time.localtime(x["starts_at"] or 0)),
             time.strftime("%H:%M:%S", time.localtime(x["ends_at"] or 0)),
             int(float(x["ends_at"] or 0) - time.time())))
print("queued lotu:", c.execute("SELECT COUNT(*) FROM lots WHERE status='queued'").fetchone()[0])
for x in c.execute("SELECT id,status,starts_at,ends_at FROM lots WHERE starts_at IS NOT NULL ORDER BY id DESC LIMIT 6"):
    print("lot %s %-8s %s -> %s" % (x["id"], x["status"],
                                    time.strftime("%H:%M:%S", time.localtime(x["starts_at"] or 0)),
                                    time.strftime("%H:%M:%S", time.localtime(x["ends_at"] or 0))))
print("dabar:", time.strftime("%H:%M:%S"))
