#!/usr/bin/env python3
# 5a TESTAS: REALIOS _vp() funkcijos (is VPS app.py, AST) simuliacija su tikru smegenys.json.
# Tikslas: 60 kvietimu -> >=26 skirtingu is 30; fiksuojam 2-is-eiles vienodus ir top3.
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

SRC = "/workspace/_app_live_vp2.py"
text = open(SRC, encoding="utf-8").read()
tree = ast.parse(text)

WANT = {"_VP_RECENT", "_VP_LAST", "_VP_PHONE_ROUND", "_vp", "_vp_names_lt"}
parts = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in WANT for t in node.targets):
        parts.append(ast.get_source_segment(text, node))
    if isinstance(node, ast.FunctionDef) and node.name in WANT:
        parts.append(ast.get_source_segment(text, node))
print("Is VPS app.py AST iskirpta daliu: %d (turi buti 5)" % len(parts))
if len(parts) != 5:
    raise SystemExit("STOP: neradau visu _vp daliu")

brain = json.load(open("/workspace/_smegenys_live.json", encoding="utf-8"))
ns = {"_vk_random": random, "time": time, "deque": deque, "vilko_brain": lambda: brain}
exec("\n".join(parts), ns)
_vp = ns["_vp"]
_vp_names_lt = ns["_vp_names_lt"]

PHONE_ALL = [p["id"] for p in brain["frazes"]["phone"] if p.get("aktyvi", True) and p.get("tekstas")]
FB = ["Alio, alio!"]
ids, txts = [], []
for i in range(60):
    r = _vp("phone", 1000 + i * 7, FB)
    ids.append(r["phrase_id"])
    txts.append(r["text"])
    time.sleep(0.001)
c = Counter(ids)
consec = sum(1 for i in range(1, 60) if ids[i] == ids[i - 1])
print()
print("=== 5a) 60 kvietimu _vp('phone', ...) (REALI funkcija is VPS app.py) ===")
print("SKIRTINGU fraziu: %d/30" % len(c))
print("2-is-eiles vienodu: %d" % consec)
print("top3 pasikartojimai: %s" % c.most_common(3))
print("neraudotos frazes: %s" % sorted(set(PHONE_ALL) - set(ids)))
print("ar visi tekstai ne tusciai: %s" % all(bool(t) for t in txts))

print()
print("=== 5a2) phone_catchup pool (12 kvietimu) ===")
cids = []
for i in range(12):
    r = _vp("phone_catchup", 2000 + i * 13, FB)
    cids.append(r["phrase_id"])
    time.sleep(0.001)
cc = Counter(cids)
print("SKIRTINGU: %d/30 | top3=%s" % (len(cc), cc.most_common(3)))

print()
print("=== 5a3) _vp_names_lt() ({vardai} uzpildymas) ===")
for sample in ([], ["Jonas"], ["Jonas", "Petras"], ["Jonas", "Petras", "Rasa"], ["jonas", "Jonas"]):
    print("  %-32s -> %r" % (sample, _vp_names_lt(sample)))

print()
print("=== 5a4) {vardai} pakeitimo patikra (kaip režisieryje) ===")
raw = brain["frazes"]["phone_catchup"][0]["tekstas"]
fixed = str(raw).replace("{vardai}", _vp_names_lt(["Jonas", "Petras"]) or "dalyviai")
print("  pries : %s" % raw)
print("  po    : %s" % fixed)
print("  liko '{vardai}': %s" % ("{vardai}" in fixed))
left = [p["id"] for p in brain["frazes"]["phone_catchup"] if "{vardai}" in str(p.get("tekstas") or "")]
print("  fraziu su {vardai} is viso: %d/%d" % (len(left), len(brain["frazes"]["phone_catchup"])))
