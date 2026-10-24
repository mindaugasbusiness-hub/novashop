#!/usr/bin/env python3
# Lokalus pagalbinis irankis: vykdo komandas VPS per SSH (paramiko).
# Naudojimas:  AUKC_PW='...' python3 _vps.py "komanda1" "komanda2"
# Slaptazodis imamas is aplinkos kintamojo AUKC_PW ir NIEKADA nespausdinamas.
import os
import sys

import paramiko

HOST = os.environ.get("AUKC_HOST", "5.175.171.113")
USER = os.environ.get("AUKC_USER", "root")
PW = os.environ.get("AUKC_PW")
PORT = int(os.environ.get("AUKC_PORT", "22"))

if not PW:
    print("NERA AUKC_PW", file=sys.stderr)
    sys.exit(2)

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=20,
            allow_agent=False, look_for_keys=False)

args = sys.argv[1:]
if args and args[0] == "--put":
    sftp = cli.open_sftp()
    sftp.put(args[1], args[2])
    print("UPLOADED", args[1], "->", args[2], sftp.stat(args[2]).st_size, "baitai")
    sftp.close()
    cli.close()
    sys.exit(0)

for cmd in args:
    print("=== CMD:", cmd)
    _in, out, err = cli.exec_command(cmd, timeout=180)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    rc = out.channel.recv_exit_status()
    sys.stdout.write(o)
    if e.strip():
        sys.stdout.write("--- stderr ---\n" + e)
    print("=== RC:", rc)
cli.close()
