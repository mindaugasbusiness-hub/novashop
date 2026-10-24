#!/usr/bin/env python3
# Lokalus pagalbinis irankis: nuskaityti failus is VPS per SSH/SFTP (paramiko).
# Naudojimas: python3 _vp_fetch.py <remote> <local> [<remote2> <local2> ...]
# Slaptazodis imamas is /workspace/.aukc_env (AUKC_PW) ir NIEKADA nespausdinamas.
import os
import sys

import paramiko

env = {}
with open("/workspace/.aukc_env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

HOST = env.get("AUKC_HOST", "5.175.171.113")
USER = env.get("AUKC_USER", "root")
PW = env.get("AUKC_PW")
PORT = int(env.get("AUKC_PORT", "22"))
if not PW:
    print("NERA AUKC_PW", file=sys.stderr)
    sys.exit(2)

pairs = sys.argv[1:]
if not pairs or len(pairs) % 2:
    print(__doc__, file=sys.stderr)
    sys.exit(2)

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30,
            allow_agent=False, look_for_keys=False, banner_timeout=30, auth_timeout=30)
sftp = cli.open_sftp()
for i in range(0, len(pairs), 2):
    r, l = pairs[i], pairs[i + 1]
    sftp.get(r, l)
    print("GET", r, "->", l, os.path.getsize(l), "baitai")
sftp.close()
cli.close()
