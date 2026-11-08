# -*- coding: utf-8 -*-
"""K2: tool_agent + fetch_url (interneto skaitymas) + daugiau zingsniu."""
import io
import shutil
import sys

P = r"C:\Users\viliu\CLINE\ai-stack\tool_agent.py"
with io.open(P, "r", encoding="utf-8") as f:
    s = f.read()

if "fetch_url" in s:
    print("jau yra")
    sys.exit(0)

# 1) irankis i TOOLS sarasa
inkaras = '''    {"type": "function", "function": {
        "name": "run_powershell", "description": "PowerShell komanda (reikia leidimo; be trynimo)",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}}, "required": ["command"]}}},
]'''
naujas = '''    {"type": "function", "function": {
        "name": "run_powershell", "description": "PowerShell komanda (reikia leidimo; be trynimo)",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "Nuskaityti interneto puslapi (dokumentacija, straipsnis) ir gauti teksta",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}, "max_chars": {"type": "integer"}},
            "required": ["url"]}}},
]'''
if inkaras not in s:
    sys.exit("nerastas TOOLS inkaras")
s = s.replace(inkaras, naujas, 1)

# 2) fetch_url realizacija (pries "return 'Nezymomas irankis'")
ink2 = '        return "Nezymomas irankis: %s" % name'
real = '''        if name == "fetch_url":
            import re as _re
            import urllib.request as _u
            url = str(a.get("url") or "")
            if not url.startswith("http"):
                return "KLAIDA: reikia http(s) nuorodos"
            req = _u.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
                "Accept-Language": "lt,en;q=0.8"})
            with _u.urlopen(req, timeout=45) as r:
                html = r.read(600000).decode("utf-8", "replace")
            html = _re.sub(r"(?is)<script.*?</script>", " ", html)
            html = _re.sub(r"(?is)<style.*?</style>", " ", html)
            txt = _re.sub(r"(?s)<[^>]+>", " ", html)
            txt = _re.sub(r"&nbsp;?", " ", txt)
            txt = _re.sub(r"[ \\t\\r\\f\\v]+", " ", txt)
            txt = _re.sub(r"\\n\\s*\\n+", "\\n", txt).strip()
            riba = int(a.get("max_chars") or 6000)
            return txt[:riba] or "(tuscias puslapis)"
        return "Nezymomas irankis: %s" % name'''
if ink2 not in s:
    sys.exit("nerastas return inkaras")
s = s.replace(ink2, real, 1)

# 3) daugiau zingsniu
s = s.replace("        for _ in range(8):", "        for _ in range(12):", 1)
s = s.replace("Iki 8 zingsniu", "Iki 12 zingsniu")

# 4) sistema: leisti naudotis internetu
s = s.replace('"NIEKO NETRINK. Jei uzduociai reikia keitimu, o tau neleista - "',
              '"Gali naudotis fetch_url internete dokumentacijai susirasti. NIEKO NETRINK. "\n    '
              '"Jei uzduociai reikia keitimu, o tau neleista - "', 1)

shutil.copy2(P, P + ".bak-2026-11-08-fetch")
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)

import py_compile
try:
    py_compile.compile(P, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(P + ".bak-2026-11-08-fetch", P)
    sys.exit("SINTAKSE: %s" % e)
print("PATAISYTA: fetch_url + 12 zingsniu")
