#!/usr/bin/env python3
# JS puses catchup/{vardai} logika + emit_event 'phone' apdorojimas.
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
    ("sed -n '8880,8925p' /opt/aukcionas/app.py", "SED 8880-8925"),
    ("sed -n '6485,6510p' /opt/aukcionas/app.py", "SED 6485-6510"),
    ("sed -n '5625,5660p' /opt/aukcionas/app.py", "SED 5625-5660"),
    ("grep -n 'catchup' /opt/aukcionas/app.py", "GREP catchup"),
    ("grep -n 'def emit_event' /opt/aukcionas/app.py", "GREP emit_event def"),
]
for cmd, label in CMDS:
    rc, o, e = sh(cmd)
    print("=== %s (rc=%s) ===" % (label, rc))
    print(o.rstrip())
    if e.strip():
        print("ERR:", e.strip()[:300])
    print()
cli.close()
