#!/usr/bin/env python3
# Patch: produkto (siulomo telefono) foto item korteleje sumazinimas 25% ir pastumimas i kaire.
# Keiciama TIK .art img taisykle (desktop eil. 4056, mobile media eil. 4629).
# Nieko netrinama; pries tai daromas backup app.py.bak-photo-<data>.
import datetime
import os
import sys
import time

import paramiko

HOST = os.environ.get("AUKC_HOST", "5.175.171.113")
USER = os.environ.get("AUKC_USER", "root")
PW = os.environ.get("AUKC_PW")
PORT = int(os.environ.get("AUKC_PORT", "22"))
if not PW:
    print("NERA AUKC_PW", file=sys.stderr)
    sys.exit(2)

REMOTE = "/opt/aukcionas/app.py"

OLD = ".art img{flex:1 1 0;min-width:0;width:100%;max-height:340px;object-fit:contain;object-position:20% center;display:block;margin:0;padding:0;border:0;}"
NEW = ".art img{flex:0 0 75%;min-width:0;width:75%;max-height:255px;object-fit:contain;object-position:0% center;display:block;margin:0;padding:0;border:0;}"

OLD_M = "  .art img{max-height:300px;}"
NEW_M = "  .art img{max-height:225px;}"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30,
            allow_agent=False, look_for_keys=False, banner_timeout=30, auth_timeout=30)


def sh(cmd, t=300):
    _i, out, err = cli.exec_command(cmd, timeout=t)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    rc = out.channel.recv_exit_status()
    return rc, o, e


stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
bak = REMOTE + ".bak-photo-" + stamp
rc, o, e = sh("cp -n %s %s; ls -la %s" % (REMOTE, bak, bak))
print("[1] BACKUP rc=%s" % rc)
print((o or e).strip())

sftp = cli.open_sftp()
lb = "/workspace/_app_before_photo.py"
sftp.get(REMOTE, lb)
raw = open(lb, "rb").read()
sftp.close()
content = raw.decode("utf-8")
print("[2] Nuskaityta %d baitu, eiluciu=%d" % (len(raw), content.count("\n") + 1))

for name, old, new, exp in (("desktop .art img", OLD, NEW, 1), ("mobile .art img", OLD_M, NEW_M, 1)):
    n = content.count(old)
    print("[3] %s: radau %d (tikejausi %d)" % (name, n, exp))
    if n != exp:
        sys.exit("STOP: netiketas atitikmenu skaicius: %s" % name)
    content = content.replace(old, new)

la = "/workspace/_app_after_photo.py"
with open(la, "w", encoding="utf-8", newline="") as fh:
    fh.write(content)

lines = content.split("\n")
for i, l in enumerate(lines):
    if l.startswith(".art img{"):
        print("[4] Nauja desktop eilute %d: %s" % (i + 1, l.strip()))
    if l.strip().startswith(".art img{max-height"):
        print("[4] Nauja mobile eilute %d: %s" % (i + 1, l.strip()))

sftp = cli.open_sftp()
sftp.put(la, REMOTE)
sftp.close()
print("[5] Ikelta i %s" % REMOTE)

rc, o, e = sh("python3 -c \"import ast;ast.parse(open('%s',encoding='utf-8').read());print('SYNTAX OK')\"" % REMOTE)
print("[6] Sintakse rc=%s %s %s" % (rc, o.strip(), e.strip()))

rc, o, e = sh("systemctl restart aukcionas.service")
print("[7] restart rc=%s %s" % (rc, (o or e).strip()))
time.sleep(30)

rc, o, e = sh("systemctl is-active aukcionas.service")
print("[8] is-active: %s" % o.strip())
rc, o, e = sh("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/")
print("[9] site / : %s" % o.strip())
rc, o, e = sh("grep -n '^.art img{' %s; grep -n '.art img{max-height' %s" % (REMOTE, REMOTE))
print("[10] Galutines eilutes:")
print(o.strip())
cli.close()
print("DONE")
