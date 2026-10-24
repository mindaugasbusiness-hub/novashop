#!/usr/bin/env python3
# Skaitymas: _vp(), phone_catchup naudojimas, auto ciklas (tik skaitymas).
import sys
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


def sh(cmd, t=120):
    _i, out, err = cli.exec_command(cmd, timeout=t)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return out.channel.recv_exit_status(), o, e


CMDS = [
    ("grep -n '_vp(\\|def _vp\\|_VP_RECENT\\|_VP_LAST\\|phone_catchup' /opt/aukcionas/app.py", "GREP _vp"),
    ("sed -n '2380,2450p' /opt/aukcionas/app.py", "SED 2380-2450"),
    ("sed -n '2860,2910p' /opt/aukcionas/app.py", "SED 2860-2910"),
    ("wc -l /opt/aukcionas/app.py", "WC"),
    ("ls -la /opt/aukcionas/app.py.bak* | tail -5", "BAK"),
]
for cmd, label in CMDS:
    rc, o, e = sh(cmd)
    print("=== %s (rc=%s) ===" % (label, rc))
    print(o.rstrip())
    if e.strip():
        print("ERR:", e.strip()[:400])
    print()
cli.close()
