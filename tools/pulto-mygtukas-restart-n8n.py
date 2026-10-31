#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULTO MYGTUKAS „RESTARTUOTI N8N" — paruoštas kodas valdymo pultui (:8790).

Kodėl: n8n (:5678) krenta po Windows perkrovimo, o prievadas :5679 atrodo „neveikiantis".
Iš tikrųjų :5679 yra to paties n8n proceso vidinis Task Broker
(N8N_RUNNERS_TASK_BROKER_PORT), todėl pultas jį rodo kaip atskirą „servisą".
Mygtukas kviečia act('/restart-n8n') -> tools/n8n/restart-n8n.ps1.

Šis failas NIEKO NETRINA: jei pultas.py randamas, padaroma .bak-<data> kopija.

Naudojimas:
    python pulto-mygtukas-restart-n8n.py --self-test       # savitikra
    python pulto-mygtukas-restart-n8n.py --html            # mygtuko HTML
    python pulto-mygtukas-restart-n8n.py --python          # handler'io kodas
    python pulto-mygtukas-restart-n8n.py --diegti KELIAS   # įterpti į pultas.py
    python pulto-mygtukas-restart-n8n.py --tikrinti KELIAS # ar jau įterpta
"""

import os
import re
import sys
from datetime import datetime

AKCIJA = "/restart-n8n"
MYGTUKO_ID = "btn-restart-n8n"
MYGTUKO_TEKSTAS = "Restartuoti n8n"
RESTART_SKRIPTAS = r"C:\Users\M\CLINE\tools\n8n\restart-n8n.ps1"


# --- 1) MYGTUKO HTML -------------------------------------------------------
def mygtuko_html():
    """Mygtukas, kurį reikia įdėti į pulto sekciją „Riktai"."""
    return (
        '<button class="veiksmo-mygtukas" id="{mid}" type="button"\n'
        '        onclick="act(\'{akt}\')" title="Sustabdo ir iš naujo paleidžia n8n (:5678 + brokeris :5679)">\n'
        '  {tekstas}\n'
        '</button>'.format(mid=MYGTUKO_ID, akt=AKCIJA, tekstas=MYGTUKO_TEKSTAS)
    )


# --- 2) HANDLER'IO KODAS (Python, pulto pusėje) ---------------------------
def handlerio_kodas():
    """Kodas, kuris apdoroja act('/restart-n8n') ir grąžina aiškų atsakymą."""
    return '''# --- n8n perkrovimas (pridėta {data}) -----------------------------------
N8N_RESTART_SKRIPTAS = r"{skriptas}"


def restart_n8n():
    """Sustabdo n8n ir paleidžia iš naujo. Grąžina (kodas, pranešimas)."""
    if not os.path.exists(N8N_RESTART_SKRIPTAS):
        return 500, "NERASTA: " + N8N_RESTART_SKRIPTAS
    komanda = [
        "powershell.exe", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-File", N8N_RESTART_SKRIPTAS,
    ]
    try:
        rez = subprocess.run(komanda, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return 504, "n8n perkrovimas užtruko ilgiau nei 180 s"
    eilutes = (rez.stdout or "").strip().splitlines()
    paskutine = eilutes[-1] if eilutes else ""
    if rez.returncode == 0:
        return 200, "n8n perkrautas. " + paskutine
    return 500, "n8n perkrovimas NEPAVYKO (kodas {{0}}). {{1}}".format(
        rez.returncode, paskutine)
'''.format(data=datetime.now().strftime("%Y-%m-%d"), skriptas=RESTART_SKRIPTAS)


def marsrutizavimo_kodas():
    """Kaip prijungti act('/restart-n8n') prie esamo pulto maršrutizavimo."""
    return '''# Pulto maršrutizavime (ten, kur apdorojami act('/...') veiksmai):
if veiksmas == "{akt}":
    kodas, pranesimas = restart_n8n()
    return json_response({{"ok": kodas == 200, "kodas": kodas, "pranesimas": pranesimas}})
'''.format(akt=AKCIJA)


# --- 3) ĮTERPIMO LOGIKA (saugi, su .bak kopija) ----------------------------
def rasti_veiksmu_sekcija(tekstas):
    """Grąžina (pradžia, pabaiga) sekcijos „Riktai"/„Veiksmai", arba (None, None)."""
    for uz in ("Riktai", "RIKTAI", "Veiksmai", "VEIKSMAI", "Valdymas"):
        m = re.search(re.escape(uz), tekstas)
        if m:
            return m.start(), m.end()
    return None, None


def ideti_mygtuka(tekstas):
    """Įterpia mygtuką į „Riktai" sekciją. Grąžina (naujas_tekstas, ar_pavyko)."""
    if MYGTUKO_ID in tekstas:
        return tekstas, False  # jau yra -- nedvigubiname
    pradzia, pabaiga = rasti_veiksmu_sekcija(tekstas)
    if pradzia is None:
        return tekstas, False
    m = re.search(r"</(section|div|fieldset)>", tekstas[pabaiga:])
    vieta = pabaiga + m.start() if m else pabaiga
    naujas = tekstas[:vieta] + "\n" + mygtuko_html() + "\n" + tekstas[vieta:]
    return naujas, True


def ideti_handleri(tekstas):
    """Įterpia restart_n8n() prieš `if __name__` arba failo gale."""
    if "def restart_n8n(" in tekstas:
        return tekstas, False
    kodas = handlerio_kodas()
    m = re.search(r"^if __name__ ==", tekstas, re.MULTILINE)
    vieta = m.start() if m else len(tekstas)
    naujas = tekstas[:vieta] + kodas + "\n\n" + tekstas[vieta:]
    return naujas, True


def skaityti(kelias):
    with open(kelias, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def irasyti_su_kopija(kelias, tekstas):
    """1 taisyklė: prieš perrašant padaroma .bak kopija."""
    kopija = "{0}.bak-{1}".format(kelias, datetime.now().strftime("%Y%m%d_%H%M%S"))
    if os.path.exists(kelias):
        with open(kopija, "w", encoding="utf-8") as f:
            f.write(skaityti(kelias))
    with open(kelias, "w", encoding="utf-8") as f:
        f.write(tekstas)
    return kopija


def pataisyk_faila(kelias, sausa=False):
    """Pilnas įterpimas į pultas.py. sausa=True -> tik parodo, ką darytų."""
    if not os.path.exists(kelias):
        return {"ok": False, "pranesimas": "NERASTA: " + kelias, "kopija": None}
    tekstas = skaityti(kelias)
    naujas, m_ok = ideti_mygtuka(tekstas)
    naujas, h_ok = ideti_handleri(naujas)
    if not m_ok and not h_ok:
        return {"ok": True, "kopija": None,
                "pranesimas": "Jau įterpta anksčiau -- nieko nekeičiu"}
    if sausa:
        return {"ok": True, "kopija": None,
                "pranesimas": "SAUSAS REŽIMAS: mygtukas={0}, handler={1}".format(m_ok, h_ok)}
    kopija = irasyti_su_kopija(kelias, naujas)
    return {"ok": True, "kopija": kopija,
            "pranesimas": "Įterpta: mygtukas={0}, handler={1}".format(m_ok, h_ok)}


# --- 4) SAVITIKRA ----------------------------------------------------------
PULTO_PAVYZDYS = '''import json, os, subprocess

HTML = """<section class="kortele">
<h2>Riktai</h2>
<button class="veiksmo-mygtukas" onclick="act('/perkrauti-viska')">Perkrauti viską</button>
</section>"""


def act(veiksmas):
    return json_response({"ok": True})


if __name__ == "__main__":
    paleisti()
'''


def self_test():
    import tempfile

    klaidos = 0
    atvejai = []

    html = mygtuko_html()
    atvejai.append(("mygtuke yra act('/restart-n8n')", AKCIJA in html, True))
    atvejai.append(("mygtuke yra id", MYGTUKO_ID in html, True))
    atvejai.append(("mygtuko tekstas lietuviškas", MYGTUKO_TEKSTAS in html, True))

    handler = handlerio_kodas()
    atvejai.append(("handler'is turi restart_n8n()", "def restart_n8n(" in handler, True))
    atvejai.append(("handler'is kviečia restart-n8n.ps1",
                    "restart-n8n.ps1" in handler, True))
    atvejai.append(("handler'is turi timeout", "timeout=180" in handler, True))

    naujas, ok1 = ideti_mygtuka(PULTO_PAVYZDYS)
    atvejai.append(("mygtukas iterptas i Riktai sekcija", ok1, True))
    atvejai.append(("mygtukas prieš </section>",
                    naujas.index(MYGTUKO_ID) < naujas.index("</section>"), True))
    atvejai.append(("senas mygtukas neištrintas", "/perkrauti-viska" in naujas, True))

    _, ok2 = ideti_mygtuka(naujas)
    atvejai.append(("antrą kartą nedvigubina mygtuko", ok2, False))

    su_handler, ok3 = ideti_handleri(naujas)
    atvejai.append(("handler'is įterptas", ok3, True))
    atvejai.append(("handler'is prieš if __name__",
                    su_handler.index("def restart_n8n(") < su_handler.index('if __name__'),
                    True))
    atvejai.append(("kodas lieka validus (compile)", bool(compile(su_handler, "x", "exec")), True))

    be_riktu, ok4 = ideti_mygtuka("import os\nprint('labas')\n")
    atvejai.append(("be Riktai sekcijos nieko negeria", ok4, False))
    atvejai.append(("tekstas nepakitęs", be_riktu == "import os\nprint('labas')\n", True))

    # pilnas ciklas su laikinu failu + .bak kopija
    sukurta_kopija = None
    with tempfile.TemporaryDirectory() as d:
        kelias = os.path.join(d, "pultas.py")
        with open(kelias, "w", encoding="utf-8") as f:
            f.write(PULTO_PAVYZDYS)
        rez = pataisyk_faila(kelias)
        atvejai.append(("pataisyk_faila ok", rez["ok"], True))
        sukurta_kopija = rez["kopija"]
        atvejai.append(("padaryta .bak kopija", bool(sukurta_kopija), True))
        atvejai.append((".bak kopija egzistuoja",
                        os.path.exists(sukurta_kopija) if sukurta_kopija else False, True))
        if sukurta_kopija and os.path.exists(sukurta_kopija):
            atvejai.append((".bak turi SENĄ turinį",
                            MYGTUKO_ID not in skaityti(sukurta_kopija), True))
        atvejai.append(("naujame faile yra mygtukas",
                        MYGTUKO_ID in skaityti(kelias), True))
        atvejai.append(("pakartotinas paleidimas nieko nekeičia",
                        "nieko nekeičiu" in pataisyk_faila(kelias)["pranesimas"], True))
        atvejai.append(("nerastas failas -> ok=False",
                        pataisyk_faila(os.path.join(d, "nera.py"))["ok"], False))

    for pavadinimas, gauta, tiketa in atvejai:
        ar_ok = gauta == tiketa
        if not ar_ok:
            klaidos += 1
        print("{0}  {1:<44} gauta={2!r}".format("PASS" if ar_ok else "FAIL",
                                                pavadinimas, gauta))
    print("")
    print("{0}/{1} patikrų praėjo".format(len(atvejai) - klaidos, len(atvejai)))
    return 1 if klaidos else 0


def tikrinti_faila(kelias):
    """Ar pulte jau yra mygtukas ir handler'is."""
    if not os.path.exists(kelias):
        print("NERASTA: " + kelias)
        return 1
    tekstas = skaityti(kelias)
    yra_mygtukas = MYGTUKO_ID in tekstas
    yra_handler = "def restart_n8n(" in tekstas
    print("{0}: mygtukas={1}, handler={2}".format(
        kelias, "TAIP" if yra_mygtukas else "NE", "TAIP" if yra_handler else "NE"))
    return 0 if (yra_mygtukas and yra_handler) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv or "-t" in argv:
        return self_test()
    if "--html" in argv:
        print(mygtuko_html())
        return 0
    if "--python" in argv:
        print(handlerio_kodas())
        print(marsrutizavimo_kodas())
        return 0
    if "--tikrinti" in argv:
        i = argv.index("--tikrinti")
        if len(argv) <= i + 1:
            print("Trūksta kelio: --tikrinti C:\\Users\\M\\CLINE\\pultas\\pultas.py")
            return 2
        return tikrinti_faila(argv[i + 1])
    if "--diegti" in argv:
        i = argv.index("--diegti")
        if len(argv) <= i + 1:
            print("Trūksta kelio: --diegti C:\\Users\\M\\CLINE\\pultas\\pultas.py")
            return 2
        sausa = "--sausai" in argv
        rez = pataisyk_faila(argv[i + 1], sausa=sausa)
        print(rez["pranesimas"])
        if rez.get("kopija"):
            print("Kopija: " + rez["kopija"])
        if rez["ok"] and not sausa:
            print("Toliau: perkrauk pultą ir patikrink http://127.0.0.1:8790/")
        return 0 if rez["ok"] else 1
    print(__doc__)
    print("Komandos: --self-test | --html | --python | --tikrinti KELIAS | --diegti KELIAS [--sausai]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

