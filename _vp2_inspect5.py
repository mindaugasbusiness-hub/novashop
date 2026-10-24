#!/usr/bin/env python3
# JS 8940-9010 (phone event apdorojimas), phoneCatchupLine, recent bidu vardu paieska.
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
    ("sed -n '8940,9010p' /opt/aukcionas/app.py", "SED 8940-9010"),
    ("sed -n '5595,5625p' /opt/aukcionas/app.py", "SED phoneCatchupLine"),
    ("grep -n 'def get_bids\\|def recent_bids\\|FROM bids\\|def _recent' /opt/aukcionas/app.py | head -30", "GREP bids"),
    ("grep -n 'nickname' /opt/aukcionas/app.py | head -20", "GREP nickname"),
    ("sed -n '2690,2760p' /opt/aukcionas/app.py", "SED 2690-2760"),
]
for cmd, label in CMDS:
    rc, o, e = sh(cmd)
    print("=== %s (rc=%s) ===" % (label, rc))
    print(o.rstrip())
    if e.strip():
        print("ERR:", e.strip()[:300])
    print()
cli.close()
