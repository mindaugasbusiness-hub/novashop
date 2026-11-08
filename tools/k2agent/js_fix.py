# -*- coding: utf-8 -*-
"""K2: pataiso sugadinta JS string'a puslapyje (naujos eilutes simbolis)."""
import io
import re
import shutil
import sys

AS = r"C:\Users\viliu\CLINE\ai-stack\agent_server.py"
with io.open(AS, "r", encoding="utf-8") as f:
    a = f.read()

if 'x.veiksmai.join(" ; ")' in a:
    print("jau pataisyta")
    sys.exit(0)

start = a.find("var v = (x.veiksmai")
if start < 0:
    sys.exit("nerastas fragmentas")
end = a.find(";", a.find("x.veiksmai.join", start) if "x.veiksmai.join" in a[start:start + 400] else start)
# saugiau: ieskome pirmo ';' po 400 simboliu
end = a.find(";", start + 100)
if end < 0:
    sys.exit("nerastas pabaigos ;")

naujas = ('var v = (x.veiksmai && x.veiksmai.length) ? '
          '" | Irankiai (" + x.veiksmai.length + "): " + x.veiksmai.join(" ; ") : ""')
a = a[:start] + naujas + a[end:]

# taip pat pasalinam galima likuti su nauja eilute
a = a.replace('o.textContent = x.text + v + "\\n\\nFailas: "', 'o.textContent = x.text + v + " | Failas: "')

shutil.copy2(AS, AS + ".bak-2026-11-08-js-fix")
with io.open(AS, "w", encoding="utf-8", newline="") as f:
    f.write(a)

import py_compile
try:
    py_compile.compile(AS, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(AS + ".bak-2026-11-08-js-fix", AS)
    sys.exit("SINTAKSE: %s" % e)
print("PATAISYTA: JS string")
