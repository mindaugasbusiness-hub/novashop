#!/usr/bin/env python3
# Salina DUBLIUOTA _VP_PHONE_ROUND eilute (po dvigubo paleidimo) ir patikrina HTTP/IVR.
import ast
import datetime
import sys
import time

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


def sh(cmd, t=300):
    _i, out, err = cli.exec_command(cmd, timeout=t)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return out.channel.recv_exit_status(), o, e


REMOTE = "/opt/aukcionas/app.py"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M")
BAK = REMOTE + ".bak-vp2dup-" + STAMP
rc, o, e = sh("cp -n %s %s; ls -la %s" % (REMOTE, BAK, BAK))
print("[1] BACKUP rc=%s %s" % (rc, (o.strip() or e.strip())))

sftp = cli.open_sftp()
sftp.get(REMOTE, "/workspace/_app_before_vp2dup.py")
sftp.close()
content = open("/workspace/_app_before_vp2dup.py", "rb").read().decode("utf-8")

CRLF = "\r\n"
LINE = '_VP_PHONE_ROUND = {"key": None}  # loto ratas, kuriame Vilkas jau kalbejo telefonu (phone_catchup)' + CRLF
DOUBLE = LINE + LINE
n = content.count(DOUBLE)
print("[2] dubliuotu eiluciu poru: %d (turi buti 1)" % n)
if n != 1:
    sys.exit("STOP: poru=%d" % n)
content = content.replace(DOUBLE, LINE)
print("[3] liko _VP_PHONE_ROUND eiluciu: %d (turi buti 4: def+get+set+? )" % content.count("_VP_PHONE_ROUND"))
ast.parse(content)
with open("/workspace/_app_after_vp2dup.py", "w", encoding="utf-8", newline="") as fh:
    fh.write(content)

sftp = cli.open_sftp()
sftp.put("/workspace/_app_after_vp2dup.py", REMOTE)
sftp.close()
rc, o, e = sh("/opt/aukcionas/.venv/bin/python -c \"import ast;ast.parse(open('%s',encoding='utf-8').read());print('SYNTAX OK')\"" % REMOTE)
print("[4] Sintakse serveryje rc=%s %s %s" % (rc, o.strip(), e.strip()))
rc, o, e = sh("grep -n '_VP_PHONE_ROUND' %s" % REMOTE)
print("[5] Eilutes:\n%s" % o.strip())

rc, o, e = sh("systemctl restart aukcionas.service")
print("[6] restart rc=%s %s" % (rc, (o or e).strip()))
time.sleep(45)
rc, o, e = sh("systemctl is-active aukcionas.service")
print("[7] is-active: %s" % o.strip())
rc, o, e = sh("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/")
print("[8] HTTP / : %s" % o.strip())
rc, o, e = sh("curl -s -o /dev/null -w '%{http_code}' https://penktadienioaukcionas.lt/")
print("[9] HTTP https://penktadienioaukcionas.lt/ : %s" % o.strip())
rc, o, e = sh("curl -s -X POST http://127.0.0.1:8000/twilio/voice -d 'CallSid=T2' | head -c 160")
print("[10] IVR voice: %s" % o.strip())
rc, o, e = sh("curl -s -X POST 'http://127.0.0.1:8000/twilio/menu' -d 'Digits=1&CallSid=T2' | head -c 160")
print("[11] IVR menu: %s" % o.strip())
rc, o, e = sh("journalctl -u aukcionas.service --since '-3min' -p warning --no-pager | tail -5")
print("[12] journal warnings:\n%s" % (o.strip() or "(nera)"))

cli.close()
print("DONE backup=%s" % BAK)
