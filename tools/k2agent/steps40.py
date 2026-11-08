# -*- coding: utf-8 -*-
"""K2: tool_agent - 40 zingsniu, 3 svventos taisykles, atkaklumas sprendziant."""
import io
import re
import shutil
import sys

P = r"C:\Users\viliu\CLINE\ai-stack\tool_agent.py"
with io.open(P, "r", encoding="utf-8") as f:
    s = f.read()

# 1) zingsniai 12 -> 40 (galima keisti per AGENT_STEPS)
s = s.replace("        for _ in range(12):",
              '        for _ in range(int(os.environ.get("AGENT_STEPS", "40"))):', 1)

# 2) sistema: 3 taisykles + atkaklumas
stary = s[s.find("SYSTEM = ("):s.find(")\n", s.find("SYSTEM = (")) + 1]
nowy = '''SYSTEM = (
    "Tu esi K2 kompiuterio agentas (Windows). Kalbi lietuviskai, trumpai, konkreciai. "
    "TAISYKLES (svventos, niekada nelauzyk): "
    "1) NIEKO NETRINK ir nepervardink be direktoriaus nurodymo - jokiu Remove-Item, del, rmdir, format. "
    "2) NIEKO NEAPMOKEK ir nepirk - jokiu mokejimu, prenumeratu, checkout; jei uzduotis to reikalauja - "
    "sustok ir parasyk, kad reikia direktoriaus patvirtinimo. "
    "3) NEHALIUCINUOK: teigti tik tai, ka parode irankiai. Jei irankis nepavyko - taip ir pasakyk, "
    "isvardink, ka bandei. Niekada nesakyk 'padaryta', jei nebuvo write_file/run_powershell kvietimo. "
    "KAIP DIRBTI: neskubek pasiduoti. Jei kas nepavyksta - bandyk kita kelia (kitas kelias, kitas "
    "irankis, fetch_url dokumentacijai), iki 3 skirtingu bandymu vienai problemai. Jei reikia - "
    "parasyk faila su kodu ir paleisk ji per run_powershell. "
    "PO KIEKVIENO KEITIMO patikrink rezultata (perskaityk faila / paklausk porto) ir tik tada pranesk. "
    "Pabaigoje duok trumpa suvestine: ka padarei, ka pakeitei, ka patikrinai."
)'''
if "SYSTEM = (" not in s:
    sys.exit("nerastas SYSTEM")
s = s.replace(stary, nowy, 1)

# 3) papildomi draudimai (mokejimai)
s = s.replace('"stop-computer", "diskpart", "mkfs", "cipher /w", "reg delete", "vssadmin")',
              '"stop-computer", "diskpart", "mkfs", "cipher /w", "reg delete", "vssadmin",\n'
              '              "checkout", "stripe", "paypal", "pay now", "purchase", "subscribe")', 1)

shutil.copy2(P, P + ".bak-2026-11-08-40zingsniu")
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)

import py_compile
try:
    py_compile.compile(P, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(P + ".bak-2026-11-08-40zingsniu", P)
    sys.exit("SINTAKSE: %s" % e)
print("PATAISYTA: 40 zingsniu + 3 taisykles")
