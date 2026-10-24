#!/usr/bin/env python3
# Vykdoma VPS: /tmp/vp_check.py — patikrinimai po _vp pataisos (tik skaitymas + F11 testas).
# Slaptazodis NIEKADA nespausdinamas (imamas is systemd Environment).
import json
import re
import sqlite3
import subprocess
import time
import urllib.request

DB = "/opt/aukcionas/aukcionas.db"
BASE = "http://127.0.0.1:8000"

print("=== A) REALUS serverio ivykiai (events lentele, event_type='phone') ===")
con = sqlite3.connect(DB)
rows = con.execute(
    "SELECT event_id, payload, datetime(created_at,'unixepoch','localtime') FROM events "
    "WHERE event_type='phone' ORDER BY event_id DESC LIMIT 40"
).fetchall()
con.close()
seq = []
for eid, p, t in reversed(rows):
    try:
        d = json.loads(p)
    except Exception:
        continue
    seq.append(d.get("phrase_id"))
    print("%5s %s n=%s phrase_id=%s manual=%s | %s"
          % (eid, t, d.get("n"), d.get("phrase_id"), d.get("manual"), str(d.get("text"))[:64]))
if seq:
    print("phone ivykiu: %d | SKIRTINGU phrase_id: %d | 2-is-eiles-vienodu: %d"
          % (len(seq), len(set(seq)), sum(1 for i in range(1, len(seq)) if seq[i] == seq[i - 1])))
else:
    print("(events lenteleje phone ivykiu dar nera — praktika dar neturejo skambucio)")

print()
print("=== B) /api/admin/vilkas_phone (F11) 10x ===")
env = subprocess.run(["systemctl", "show", "aukcionas.service", "-p", "Environment"],
                     capture_output=True, text=True).stdout
m = re.search(r"AUKCIONAS_ADMIN_SLAPTAZODIS=(\S+)", env)
pw = m.group(1) if m else ""
texts = []
for i in range(10):
    body = json.dumps({"password": pw, "n": "next"}).encode()
    req = urllib.request.Request(BASE + "/api/admin/vilkas_phone", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
        texts.append(d.get("text"))
        print("%2d. n=%s core_count=%s | %s" % (i + 1, d.get("n"), d.get("core_count"), str(d.get("text"))[:64]))
    except Exception as e:
        print("%2d. KLAIDA %s: %s" % (i + 1, type(e).__name__, e))
    time.sleep(0.2)
print("F11: SKIRTINGU tekstu=%d/10" % len(set(texts)))

print()
print("=== C) Frazes smegenys.json ===")
d = json.load(open("/opt/aukcionas/vilko_mokykla/smegenys.json", encoding="utf-8"))
for k in ("phone", "phone_catchup", "joke", "nudge"):
    a = d["frazes"].get(k, [])
    akt = [x for x in a if x.get("aktyvi", True)]
    print("%-14s viso=%d aktyvios=%d panaudota(kartai>0)=%d"
          % (k, len(a), len(akt), len([x for x in akt if float(x.get("kartai") or 0) > 0])))
