#!/usr/bin/env python3
# Sync29: is DESK_SONG_TITLES isimami TIK irasai 1 ir 33 (failai NELIEČIAMI).
# Papildomai: /desk-songs/{n} route gauna priklausymo DESK_SONG_TITLES patikra,
# kad isimtos dainos duotu 404 (failai lieka vietoje).
import datetime
import os
import re
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
bak = REMOTE + ".bak-sync29-" + stamp
rc, o, e = sh("cp -n %s %s; ls -la %s" % (REMOTE, bak, bak))
print("[1] BACKUP rc=%s" % rc)
print((o.strip() or e.strip()))

sftp = cli.open_sftp()
lb = "/workspace/_app_before_sync29.py"
sftp.get(REMOTE, lb)
raw = open(lb, "rb").read()
sftp.close()
content = raw.decode("utf-8")
print("[2] Nuskaityta: %d baitu, eiluciu=%d" % (len(raw), content.count("\n") + 1))

lines = content.split("\n")
start = None
for i, l in enumerate(lines):
    if l.startswith("DESK_SONG_TITLES = {"):
        start = i
        break
if start is None:
    sys.exit("STOP: neradau DESK_SONG_TITLES pradzios")
end = None
for j in range(start, len(lines)):
    if lines[j].rstrip("\r").rstrip().endswith("}"):
        end = j
        break
if end is None:
    sys.exit("STOP: neradau bloko pabaigos")
print("[3] Blokas: eilutes %d-%d" % (start + 1, end + 1))

head = "DESK_SONG_TITLES = {"
new_block = []
removed = []
for k in range(start, end + 1):
    l = lines[k]
    nl = "\r" if l.endswith("\r") else ""
    bare = l.rstrip("\r")
    if k == start:
        rest = bare[len(head):]
        if re.match(r'\s*1:\s*"', rest):
            new_block.append(head + nl)
            removed.append(1)
            continue
        new_block.append(l)
        continue
    m = re.match(r'^\s*(\d+):\s*"', bare)
    if m and m.group(1) == "33":
        if bare.rstrip().endswith("}"):
            new_block.append("}" + nl)
        removed.append(33)
        continue
    new_block.append(l)

if removed != [1, 33]:
    sys.exit("STOP: netiketa removed=%r" % removed)

nums = re.findall(r'^\s*(\d+):\s*"', "\n".join(new_block), re.M)
print("[4] Po pakeitimo irasu: %d" % len(nums))
print("[4] Numeriai: %s" % ",".join(nums))
if len(nums) != 29 or "1" in nums or "33" in nums:
    sys.exit("STOP: neteisingas skaicius/sudetis")

new_content = "\n".join(lines[:start] + new_block + lines[end + 1:])

old_route = ('@app.get("/desk-songs/{n}")\r\n'
             'def desk_song_file(n: int):\r\n'
             '    p = desk_song_path(int(n))\r\n')
new_route = ('@app.get("/desk-songs/{n}")\r\n'
             'def desk_song_file(n: int):\r\n'
             '    if int(n) not in DESK_SONG_TITLES:\r\n'
             '        raise HTTPException(404, "nėra tos dainos")\r\n'
             '    p = desk_song_path(int(n))\r\n')
cnt = new_content.count(old_route)
if cnt != 1:
    sys.exit("STOP: route guard atitikmenys=%d" % cnt)
new_content = new_content.replace(old_route, new_route)
print("[5] Pridetas guard: /desk-songs/{n} tikrina DESK_SONG_TITLES")

la = "/workspace/_app_after_sync29.py"
with open(la, "w", encoding="utf-8", newline="") as fh:
    fh.write(new_content)

sftp = cli.open_sftp()
sftp.put(la, REMOTE)
sftp.close()
print("[6] Ikelta atgal i %s" % REMOTE)

rc, o, e = sh("python3 -c \"import ast;ast.parse(open('%s',encoding='utf-8').read());print('SYNTAX OK')\"" % REMOTE)
print("[7] Sintakses patikra rc=%s %s %s" % (rc, o.strip(), e.strip()))

rc, o, e = sh("systemctl restart aukcionas.service")
print("[8] restart rc=%s %s" % (rc, (o or e).strip()))
time.sleep(20)

rc, o, e = sh("systemctl is-active aukcionas.service")
print("[9] is-active: %s" % o.strip())

rc, o, e = sh("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/")
print("[10] site / : %s" % o.strip())

for n in (1, 5, 15, 32, 33):
    rc, o, e = sh("curl -s -o /dev/null -w '%%{http_code}' http://127.0.0.1:8000/desk-songs/%d" % n)
    print("[10] /desk-songs/%d : %s" % (n, o.strip()))

rc, o, e = sh("curl -s http://127.0.0.1:8000/api/desk_songs | python3 -c \"import sys,json;d=json.load(sys.stdin);print(len(d['items']));print(','.join(str(i['n']) for i in d['items']))\"")
print("[11] /api/desk_songs skaicius + numeriai:")
print(o.strip())

rc, o, e = sh("ls /opt/aukcionas/desk_songs/*.webm | wc -l; ls -la /opt/aukcionas/desk_songs/01.webm /opt/aukcionas/desk_songs/33.webm")
print("[12] Failai .webm (kiekis) ir 01/33:")
print(o.strip() or e.strip())

sftp = cli.open_sftp()
fh = sftp.open(REMOTE)
remote_txt = fh.read().decode("utf-8")
fh.close()
sftp.close()
rl = remote_txt.split("\n")
rs = next(i for i, l in enumerate(rl) if l.startswith("DESK_SONG_TITLES = {"))
re_end = next(j for j in range(rs, len(rl)) if rl[j].rstrip("\r").rstrip().endswith("}"))
print("[13] GALUTINIS DESK_SONG_TITLES (eil. %d-%d):" % (rs + 1, re_end + 1))
print("\n".join(rl[rs:re_end + 1]).replace("\r", ""))

cli.close()
print("DONE")
