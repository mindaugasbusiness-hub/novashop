#!/usr/bin/env python3
# Regresija: _vp() visiems smegenys.json kind'ams — grazina {"text","phrase_id"} ir ne tuscia.
import ast
import json
import random
import time
from collections import Counter, deque

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
sftp = cli.open_sftp()
sftp.get("/opt/aukcionas/app.py", "/workspace/_app_live_vp2.py")
sftp.get("/opt/aukcionas/vilko_mokykla/smegenys.json", "/workspace/_smegenys_live.json")
sftp.close()
cli.close()

text = open("/workspace/_app_live_vp2.py", encoding="utf-8").read()
tree = ast.parse(text)
WANT = {"_VP_RECENT", "_VP_LAST", "_VP_PHONE_ROUND", "_vp", "_vp_names_lt"}
parts = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in WANT for t in node.targets):
        parts.append(ast.get_source_segment(text, node))
    if isinstance(node, ast.FunctionDef) and node.name in WANT:
        parts.append(ast.get_source_segment(text, node))

brain = json.load(open("/workspace/_smegenys_live.json", encoding="utf-8"))
ns = {"_vk_random": random, "time": time, "deque": deque, "vilko_brain": lambda: brain}
exec("\n".join(parts), ns)
_vp = ns["_vp"]

print("=== Regresija: _vp() visiems kind'ams (5 kvietimai kiekvienam) ===")
bad = 0
for kind, arr in sorted((brain.get("frazes") or {}).items()):
    akt = [p for p in arr if p.get("aktyvi", True) and p.get("tekstas")]
    if not akt:
        print("%-18s (nėra aktyvių) — praleista" % kind)
        continue
    ids, txt = [], []
    for i in range(5):
        r = _vp(kind, 700 + i, ["FB"])
        ids.append(r.get("phrase_id"))
        txt.append(str(r.get("text") or ""))
        time.sleep(0.001)
    ok = all(txt) and all(ids)
    if not ok:
        bad += 1
    print("%-18s aktyviu=%-4d SKIRTINGU=%d/5 | phrase_id=%-18s | %s"
          % (kind, len(akt), len(set(ids)), ids[0], txt[0][:44]))
print()
print("=== Krastutinis atvejis: tuscias kind (fallback) ===")
r = _vp("nera_tokio_kind", 3, ["F1", "F2", "F3"])
print("fallback -> %s (turi buti F1/F2/F3, phrase_id=None)" % r)
r2 = _vp("nera_tokio_kind", 0, [])
print("tuscias fallback -> %s" % r2)
print()
print("BLOGA: %d (turi buti 0)" % bad)
