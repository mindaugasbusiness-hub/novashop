#!/usr/bin/env python3
# Pataisa VPS /opt/aukcionas/app.py (zr. _vp2_newfunc.py ir _vp2_newloop.py fragmentus).
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

HOST = env.get("AUKC_HOST", "5.175.171.113")
USER = env.get("AUKC_USER", "root")
PW = env.get("AUKC_PW")
PORT = int(env.get("AUKC_PORT", "22"))
if not PW:
    print("NERA AUKC_PW", file=sys.stderr)
    sys.exit(2)

REMOTE = "/opt/aukcionas/app.py"
LOCAL_BEFORE = "/workspace/_app_before_vp2.py"
LOCAL_AFTER = "/workspace/_app_after_vp2.py"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M")
BAK = REMOTE + ".bak-vp2-" + STAMP

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30,
            allow_agent=False, look_for_keys=False, banner_timeout=30, auth_timeout=30)


def sh(cmd, t=300):
    _i, out, err = cli.exec_command(cmd, timeout=t)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return out.channel.recv_exit_status(), o, e


rc, o, e = sh("cp -n %s %s; ls -la %s" % (REMOTE, BAK, BAK))
print("[1] BACKUP rc=%s %s" % (rc, (o.strip() or e.strip())))

sftp = cli.open_sftp()
sftp.get(REMOTE, LOCAL_BEFORE)
sftp.close()
content = open(LOCAL_BEFORE, "rb").read().decode("utf-8")
print("[2] Nuskaityta baitu=%d eiluciu=%d" % (len(content.encode("utf-8")), content.count("\n") + 1))

CRLF = "\r\n"
NEW_FUNC = open("/workspace/_vp2_newfunc.py", encoding="utf-8").read().replace("\n", CRLF).rstrip(CRLF) + CRLF + CRLF + CRLF
NEW_LOOP = open("/workspace/_vp2_newloop.py", encoding="utf-8").read().replace("\n", CRLF).rstrip(CRLF) + CRLF

OLD_STATE = (
    '_VP_RECENT = {}  # kind -> deque(maxlen=8) paskutiniu pasirinktu fraziu id (kad nesikartotu)' + CRLF +
    '_VP_LAST = {}    # kind -> paskutinis pasirinktas fraziu id (kad nebutu dvieju is eiles vienodu)' + CRLF
)
NEW_STATE = (
    OLD_STATE +
    '_VP_PHONE_ROUND = {"key": None}  # loto ratas, kuriame Vilkas jau kalbejo telefonu (phone_catchup)' + CRLF
)

n = content.count(OLD_STATE)
print("[3] _VP_RECENT/_VP_LAST atitikmenys: %d" % n)
if n != 1:
    sys.exit("STOP: atitikmenys=%d (turi buti 1)" % n)
content = content.replace(OLD_STATE, NEW_STATE)

i = content.index("def _vp(kind, seed, fallback_list):")
j = content.index("def _sing_hook() -> str:")
print("[4] sena _vp(): %d baitu / %d eil." % (j - i, content[i:j].count("\n")))
content = content[:i] + NEW_FUNC + content[j:]

A = "                # 3 skambučiai / ratą — KIEKVIENAS kitas seed (nesikartoja), mokykla renkasi geriausias"
B = "                joke_gate = elapsed if use_elapsed else quiet"
a = content.index(A)
b = content.index(B)
print("[5] senas phone ciklas: %d baitu / %d eil." % (b - a, content[a:b].count("\n")))
content = content[:a] + NEW_LOOP + content[b:]

ast.parse(content)
print("[6] Sintakses patikra (lokaliai) OK; naujas dydis %d baitu" % len(content.encode("utf-8")))

with open(LOCAL_AFTER, "w", encoding="utf-8", newline="") as fh:
    fh.write(content)

sftp = cli.open_sftp()
sftp.put(LOCAL_AFTER, REMOTE)
sftp.close()
print("[7] Ikelta i %s" % REMOTE)

rc, o, e = sh("/opt/aukcionas/.venv/bin/python -c \"import ast;ast.parse(open('%s',encoding='utf-8').read());print('SYNTAX OK')\"" % REMOTE)
print("[8] Sintakses patikra serveryje rc=%s %s %s" % (rc, o.strip(), e.strip()))

rc, o, e = sh("grep -n '_VP_PHONE_ROUND\\|def _vp(\\|def _vp_names_lt\\|phone_catchup' %s | head -20" % REMOTE)
print("[9] Eilutes po pakeitimo:\n%s" % o.strip())

rc, o, e = sh("systemctl restart aukcionas.service")
print("[10] restart rc=%s %s" % (rc, (o or e).strip()))
time.sleep(45)

rc, o, e = sh("systemctl is-active aukcionas.service")
print("[11] is-active: %s" % o.strip())
rc, o, e = sh("curl -s -o /dev/null -w '%%{http_code}' http://127.0.0.1:8000/")
print("[12] HTTP / : %s" % o.strip())
rc, o, e = sh("curl -s -X POST http://127.0.0.1:8000/twilio/voice -d 'CallSid=T2' | head -c 200")
print("[13] IVR /twilio/voice rc=%s: %s" % (rc, o.strip()))
rc, o, e = sh("curl -s -X POST 'http://127.0.0.1:8000/twilio/menu' -d 'Digits=1&CallSid=T2' | head -c 200")
print("[14] IVR /twilio/menu rc=%s: %s" % (rc, o.strip()))

cli.close()
print("DONE backup=%s" % BAK)
