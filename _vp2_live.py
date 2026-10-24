#!/usr/bin/env python3
# Gyvas patikrinimas: events lentele (phone ivykiai, catchup veliavele), loto busena, IVR, site.
import json
import sqlite3

import paramiko

env = {}
with open("/workspace/.aukc_env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(env["AUKC_HOST"], port=int(env.get("AUKC_PORT", "22")), username=env["AUKC_USER"],
            password=env["AUKC_PW"], timeout=30, allow_agent=False, look_for_keys=False,
            banner_timeout=30, auth_timeout=30)


def sh(cmd, t=180):
    _i, out, err = cli.exec_command(cmd, timeout=t)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return out.channel.recv_exit_status(), o, e


REMOTE = r'''
import json, sqlite3
con = sqlite3.connect("/opt/aukcionas/aukcionas.db")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT event_id,payload,datetime(created_at,'unixepoch','localtime') t FROM events "
                   "WHERE event_type='phone' ORDER BY event_id DESC LIMIT 20").fetchall()
seq, cw = [], 0
for r in reversed(rows):
    try:
        d = json.loads(r["payload"])
    except Exception:
        continue
    seq.append(d.get("phrase_id"))
    if d.get("catchup"):
        cw += 1
    print("%6s %s n=%-3s phrase=%-14s catchup=%-5s manual=%-5s | %s"
          % (r["event_id"], r["t"], d.get("n"), d.get("phrase_id"), bool(d.get("catchup")),
             bool(d.get("manual")), str(d.get("text"))[:60]))
print("phone ivykiu: %d | SKIRTINGU phrase_id: %d | 2-is-eiles vienodu: %d | catchup ivykiu: %d"
      % (len(seq), len(set(seq)), sum(1 for i in range(1, len(seq)) if seq[i] == seq[i-1]), cw))
lot = con.execute("SELECT id,status,title,datetime(starts_at,'unixepoch','localtime') st FROM lots "
                  "WHERE status IN ('live','ended') ORDER BY id DESC LIMIT 3").fetchall()
for l in lot:
    print("lotas %s status=%s start=%s | %s" % (l["id"], l["status"], l["st"], str(l["title"])[:40]))
con.close()
'''
rc, o, e = sh("/opt/aukcionas/.venv/bin/python - <<'PYEOF'\n%s\nPYEOF" % REMOTE, t=120)
print("=== EVENTS (phone) ===")
print(o.strip())
if e.strip():
    print("STDERR:", e.strip()[:400])

print()
print("=== IVR + SITE ===")
for cmd, label in (
    ("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", "site 127.0.0.1:8000"),
    ("curl -s -o /dev/null -w '%{http_code}' https://penktadienioaukcionas.lt/", "site public"),
    ("curl -s -X POST http://127.0.0.1:8000/twilio/voice -d 'CallSid=T2' | head -c 130", "IVR /twilio/voice"),
    ("curl -s -X POST 'http://127.0.0.1:8000/twilio/menu' -d 'Digits=1&CallSid=T2' | head -c 130", "IVR /twilio/menu"),
    ("systemctl is-active aukcionas.service", "service"),
):
    rc, o, e = sh(cmd)
    print("%-22s -> %s" % (label, o.strip() or e.strip()))
cli.close()
