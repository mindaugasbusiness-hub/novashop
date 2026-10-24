#!/usr/bin/env python3
# Diagnostika: kodel publika https://.../api/admin/vilkas_phone grazina HTTPError.
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
import json, re, subprocess, urllib.request, urllib.error
env = subprocess.run(["systemctl","show","aukcionas.service","-p","Environment"],capture_output=True,text=True).stdout
pw = (re.search(r"AUKCIONAS_ADMIN_SLAPTAZODIS=(\S+)", env) or [None,""])[1]
body = json.dumps({"password": pw}).encode()
for url in ("https://penktadienioaukcionas.lt/api/admin/vilkas_phone", "http://127.0.0.1:8000/api/admin/vilkas_phone"):
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(url, "->", r.status, r.read().decode()[:120])
    except urllib.error.HTTPError as e:
        print(url, "-> HTTPError", e.code, "| server:", e.headers.get("Server"), "| cf-ray:", e.headers.get("cf-ray"))
        print("   body:", e.read().decode("utf-8","replace")[:300].replace("\n"," "))
    except Exception as e:
        print(url, "->", type(e).__name__, e)
print("PRACTICE_BOTS env:", re.search(r"PRACTICE_BOTS=(\S+)", env).group(1) if re.search(r"PRACTICE_BOTS=(\S+)", env) else "(nenustatyta)")
print("PUBLIC_BASE_URL:", re.search(r"PUBLIC_BASE_URL=(\S+)", env).group(1) if re.search(r"PUBLIC_BASE_URL=(\S+)", env) else "(nenustatyta)")
'''
rc, o, e = sh("/opt/aukcionas/.venv/bin/python - <<'PYEOF'\n%s\nPYEOF" % REMOTE, t=120)
print(o.strip())
if e.strip():
    print("STDERR:", e.strip()[:500])

# nginx/cloudflare puse
for cmd, label in (
    ("curl -s -o /dev/null -w '%{http_code}' -X POST https://penktadienioaukcionas.lt/api/admin/vilkas_phone -H 'Content-Type: application/json' -d '{\"password\":\"x\"}'", "public POST neteisingas pw"),
    ("grep -n 'vilkas_phone' /etc/nginx/sites-enabled/* 2>/dev/null | head", "nginx vilkas_phone"),
    ("grep -rn 'vilkas_phone' /opt/aukcionas/*.py | grep -v 'app.py' | head", "kiti failai"),
    ("sqlite3 /opt/aukcionas/aukcionas.db \"SELECT unique_key FROM events WHERE event_type='phone' ORDER BY event_id DESC LIMIT 8;\"", "phone unique_key"),
):
    rc, o, e = sh(cmd)
    print("--- %s -> %s" % (label, (o.strip() or e.strip())[:300]))
cli.close()
