#!/usr/bin/env python3
# smegenys.json phone / phone_catchup statistika (tik skaitymas) + kopija lokaliai.
import json
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
sftp.get("/opt/aukcionas/vilko_mokykla/smegenys.json", "/workspace/_smegenys_vp2.json")
sftp.close()
cli.close()

d = json.load(open("/workspace/_smegenys_vp2.json", encoding="utf-8"))
for k in ("phone", "phone_catchup"):
    arr = d["frazes"].get(k, [])
    akt = [x for x in arr if x.get("aktyvi", True)]
    print("=== %s: viso=%d aktyvios=%d ===" % (k, len(arr), len(akt)))
    tot = 0.0
    for x in akt:
        kartai = float(x.get("kartai") or 0)
        tot += kartai
    mean = tot / max(1, len(akt))
    print("kartai suma=%.0f vidurkis=%.1f" % (tot, mean))
    for x in sorted(akt, key=lambda z: -float(z.get("kartai") or 0)):
        print("  %-14s a=%-6s b=%-6s kartai=%-7s tekste=%s"
              % (x.get("id"), x.get("a"), x.get("b"), x.get("kartai"), str(x.get("tekstas"))[:52]))
