#!/usr/bin/env python3
# Papildomas skaitymas: {vardai} apdorojimas, F11 endpointas, eil. 900-935, 2250-2280, emit_event 'phone'.
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
    ("grep -n 'vardai' /opt/aukcionas/app.py | head -40", "GREP vardai"),
    ("grep -n 'def api_admin_vilkas_phone' /opt/aukcionas/app.py", "GREP F11 def"),
    ("sed -n '2250,2290p' /opt/aukcionas/app.py", "SED 2250-2290"),
    ("sed -n '915,935p' /opt/aukcionas/app.py", "SED 915-935"),
    ("sed -n '2820,2830p' /opt/aukcionas/app.py", "SED 2820-2830"),
    ("grep -n 'VILKAS8_PHONE' /opt/aukcionas/app.py | head", "GREP VILKAS8_PHONE"),
    ("grep -n 'phone' /opt/aukcionas/app.py | sed -n '1,40p'", "GREP phone 1-40"),
]
for cmd, label in CMDS:
    rc, o, e = sh(cmd)
    print("=== %s (rc=%s) ===" % (label, rc))
    print(o.rstrip())
    if e.strip():
        print("ERR:", e.strip()[:300])
    print()
cli.close()
