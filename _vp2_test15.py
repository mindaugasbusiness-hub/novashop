#!/usr/bin/env python3
# 5b TESTAS: 15 realiu POST /api/admin/vilkas_phone (F11) — kiek skirtingu tekstu.
# Slaptazodis imamas is systemd Environment (nespausdinamas).
import json
import re
import subprocess
import time
import urllib.request

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
import json, re, subprocess, time, urllib.request
env = subprocess.run(["systemctl","show","aukcionas.service","-p","Environment"],capture_output=True,text=True).stdout
m = re.search(r"AUKCIONAS_ADMIN_SLAPTAZODIS=(\S+)", env)
pw = m.group(1) if m else ""
print("slaptazodis rastas systemd env:", bool(pw))
def call(url, n=15):
    texts, ids, ns = [], [], []
    for i in range(n):
        body = json.dumps({"password": pw}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read().decode())
            texts.append(str(d.get("text") or ""))
            ids.append(d.get("phrase_id"))
            ns.append(d.get("n"))
        except Exception as e:
            texts.append("KLAIDA:%s" % type(e).__name__)
        time.sleep(0.25)
    return texts, ids, ns
t, i, n = call("http://127.0.0.1:8000/api/admin/vilkas_phone", 15)
for k in range(len(t)):
    print("%2d. n=%-4s phrase_id=%-14s | %s" % (k+1, n[k], i[k], t[k][:66]))
print("LOKALIAI 15x: SKIRTINGU tekstu=%d/15 | SKIRTINGU phrase_id=%d | 2-is-eiles vienodu=%d"
      % (len(set(t)), len(set(i)), sum(1 for x in range(1,15) if t[x]==t[x-1])))
t2, i2, n2 = call("https://penktadienioaukcionas.lt/api/admin/vilkas_phone", 3)
print("PUBLIKA 3x: %s" % [x[:40] for x in t2])
print("PUBLIKA 3x SKIRTINGU=%d/3" % len(set(t2)))
'''
rc, o, e = sh("/opt/aukcionas/.venv/bin/python - <<'PYEOF'\n%s\nPYEOF" % REMOTE, t=300)
print(o.strip())
if e.strip():
    print("STDERR:", e.strip()[:600])
cli.close()
