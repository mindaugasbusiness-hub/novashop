# -*- coding: utf-8 -*-
"""K2: fetch_url - HTTPS sertifikatu atsarginis rezimas."""
import io
import shutil
import sys

P = r"C:\Users\viliu\CLINE\ai-stack\tool_agent.py"
with io.open(P, "r", encoding="utf-8") as f:
    s = f.read()

old = '''            with _u.urlopen(req, timeout=45) as r:
                html = r.read(600000).decode("utf-8", "replace")'''
new = '''            try:
                with _u.urlopen(req, timeout=45) as r:
                    html = r.read(600000).decode("utf-8", "replace")
            except Exception:
                # atsarginis: SSL nepatikrinamas (kai truksta CA sertifikatu)
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with _u.urlopen(req, timeout=45, context=ctx) as r:
                    html = r.read(600000).decode("utf-8", "replace")'''
if old not in s:
    sys.exit("nerastas urlopen inkaras")

s = s.replace(old, new, 1)
shutil.copy2(P, P + ".bak-2026-11-08-ssl")
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)

import py_compile
try:
    py_compile.compile(P, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(P + ".bak-2026-11-08-ssl", P)
    sys.exit("SINTAKSE: %s" % e)
print("PATAISYTA: SSL fallback")
