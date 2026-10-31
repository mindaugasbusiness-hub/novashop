#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATSTATYMO SISTEMOS SAVITIKRA — patikrina, ar taškų sistema saugi ir išsami.

Ką tikrina:
  1) visi failai yra (ps1, sh, dokumentai)
  2) koduotė: .ps1 -> UTF-8 su BOM + CRLF; .sh -> LF
  3) saugumo taisyklės atstatymo skriptuose:
       - SHA256 patikra PRIEŠ atstatymą
       - dabartinės būklės kopija PRIEŠ atstatymą (.bak-pries-atstatyma / PRADINE-BUKLE)
       - sugadinto taško atmetimas
       - jokio masinio trynimo (rm -rf /, Remove-Item -Recurse be kopijos)
       - jokių slaptažodžių repo failuose
  4) dokumentų darna: 01_TASKAS.md mini 11 servisų; registre yra Nr. 1
  5) bash sintaksė (bash -n), jei bash yra

Naudojimas:  python tools/atstatymas/savitikra.py
"""

import os
import re
import subprocess
import sys

CIAPRASTAS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(CIAPRASTAS, '..', '..'))
DOKAI = os.path.join(REPO, 'CLINE', 'ATSTATYMAS')

# 11 pulto servisų prievadai -- turi būti ir tikrintuve, ir dokumente
PRIEVADAI_11 = [5678, 8099, 8766, 8091, 8090, 9222, 5679, 6333, 8792, 8795, 8790]

TIKIMI_FAILAI = [
    'patikrinti-servisus.ps1',
    'sukurkti-taskas.ps1',
    'atstatyti-tasku.ps1',
    'vps-taskas.sh',
    'test-vps-taskas.sh',
]

DRAUDZIU_SABLONAI = [
    (r'rm\s+-rf\s+/(\s|$)', 'masinis trynimas rm -rf /'),
    (r'Remove-Item\s+.*-Recurse.*-Force(?!.*bak)', 'Recurse trynimas be .bak apsaugos'),
    (r'password\s*=\s*["\'][^"\']{6,}', 'slaptažodis kode'),
    (r'auth_?token\s*=\s*["\'][^"\']{10,}', 'tokenas kode'),
]


def skaityti(kelias):
    with open(kelias, 'rb') as f:
        return f.read()


def tikrinti_ps1(kelias):
    baitai = skaityti(kelias)
    klaidos = []
    try:
        tekstas = baitai.decode('utf-8')
    except UnicodeDecodeError as e:
        return ['nėra validus UTF-8: {0}'.format(e)], ''
    turi_diakritiku = any(ord(c) > 127 for c in tekstas)
    if turi_diakritiku and not baitai.startswith(b'\xef\xbb\xbf'):
        klaidos.append('turi diakritikų be UTF-8 BOM (PowerShell 5.1 sulaužys)')
    if b'\r\n' not in baitai:
        klaidos.append('neturi CRLF eilučių pabaigų')
    if b'\n' in baitai.replace(b'\r\n', b''):
        klaidos.append('turi LF-only eilučių')
    if 'exit ' not in tekstas:
        klaidos.append("neturi 'exit' (grąžinimo kodo)")
    return klaidos, baitai.decode('utf-8-sig', 'replace')


def tikrinti_sh(kelias):
    baitai = skaityti(kelias)
    klaidos = []
    try:
        tekstas = baitai.decode('utf-8')
    except UnicodeDecodeError as e:
        return ['nėra validus UTF-8: {0}'.format(e)], ''
    if b'\r\n' in baitai:
        klaidos.append('turi CRLF (Linux shell script turi turėti LF)')
    if 'set -uo pipefail' not in tekstas and 'set -euo pipefail' not in tekstas:
        klaidos.append("neturi 'set -uo pipefail' (klaidų gaudymas)")
    return klaidos, tekstas


def tikrinti_sauguma(tekstas, failo_vardas):
    klaidos = []
    for sablonas, aprasas in DRAUDZIU_SABLONAI:
        if re.search(sablonas, tekstas, re.IGNORECASE):
            klaidos.append('saugumo pažeidimas: {0}'.format(aprasas))
    if failo_vardas == 'atstatyti-tasku.ps1':
        if 'SHA256' not in tekstas:
            klaidos.append('atstatyme nėra SHA256 vientisumo patikros')
        if 'bak-pries-atstatyma' not in tekstas:
            klaidos.append('atstatyme nėra .bak-pries-atstatyma kopijų')
        if 'PRADINE-BUKLE' not in tekstas:
            klaidos.append('atstatyme nėra dabartinės būklės kopijos (PRADINE-BUKLE)')
        if 'Sausai' not in tekstas:
            klaidos.append('atstatyme nėra -Sausai režimo')
        if 'exit 2' not in tekstas:
            klaidos.append('atstatyme nėra sugadinto taško atmetimo (exit 2)')
    if failo_vardas == 'vps-taskas.sh':
        if 'sha256sum -c' not in tekstas:
            klaidos.append('VPS atstatyme nėra sha256sum patikros')
        if 'bak-pries-atstatyma' not in tekstas:
            klaidos.append('VPS atstatyme nėra kopijos prieš atstatymą')
    if failo_vardas == 'sukurkti-taskas.ps1':
        if 'Get-FileHash' not in tekstas:
            klaidos.append('taško kūrime nėra Get-FileHash (SHA256 manifestui)')
        if 'TASKAS.json' not in tekstas:
            klaidos.append('taško kūrime nėra TASKAS.json manifesto')
    return klaidos


def tikrinti_dokumentus():
    """Ar dokumentai darna su tikrinamais 11 servisų ir registru."""
    klaidos = []
    taskas = os.path.join(DOKAI, '01_TASKAS.md')
    registras = os.path.join(DOKAI, 'atstatymo-sarasas.md')
    readme = os.path.join(DOKAI, 'README.md')

    for kelias in (taskas, registras, readme):
        if not os.path.exists(kelias):
            klaidos.append('nėra dokumento: {0}'.format(os.path.basename(kelias)))
    if klaidos:
        return klaidos

    t = open(taskas, encoding='utf-8').read()
    for p in PRIEVADAI_11:
        if str(p) not in t:
            klaidos.append('01_TASKAS.md nemini serviso prievado {0}'.format(p))
    if '11/11' not in t:
        klaidos.append('01_TASKAS.md nemini 11/11 būsenos')

    r = open(registras, encoding='utf-8').read()
    if not re.search(r'\|\s*\*\*1\*\*\s*\|', r):
        klaidos.append('registre nėra taško Nr. 1')
    if 'atstatymas-1' not in r:
        klaidos.append('registre nėra git žymos atstatymas-1')

    rd = open(readme, encoding='utf-8').read()
    if '-Sausai' not in rd:
        klaidos.append('README nemini -Sausai režimo')
    if 'niekada' not in rd.lower():
        klaidos.append('README nemini slaptų duomenų taisyklės')
    return klaidos


def tikrinti_join_path(tekstas):
    """Join-Path su VIENU argumentu iššaukia interaktyvų klausimą (ChildPath) ir užstringa.

    Būtent taip įvyko 2026-10-31: `Join-Path $CLINE_HOME` be antro argumento paklausė
    „Supply values for the following parameters: ChildPath:" ir skriptas sustojo.
    """
    klaidos = []
    for m in re.finditer(r'Join-Path\s+("[^"]+"|\$[\w:]+|\'[^\']+\')\s*(?=[\)\|,;\r\n])', tekstas):
        eilute = tekstas[:m.start()].count('\n') + 1
        klaidos.append("eilutė {0}: Join-Path su vienu argumentu (klaus interaktyviai): {1}".format(
            eilute, m.group(0).strip()))
    return klaidos


def tikrinti_tikrintuvo_prievadus():
    """Ar patikrinti-servisus.ps1 tikrina būtent tuos 11 prievadų."""
    kelias = os.path.join(CIAPRASTAS, 'patikrinti-servisus.ps1')
    if not os.path.exists(kelias):
        return ['nėra patikrinti-servisus.ps1']
    tekstas = open(kelias, encoding='utf-8-sig').read()
    truksta = [str(p) for p in PRIEVADAI_11 if str(p) not in tekstas]
    if truksta:
        return ['patikrinti-servisus.ps1 netikrina prievadų: {0}'.format(', '.join(truksta))]
    if 'Prievadas = ' not in tekstas:
        return ['patikrinti-servisus.ps1 neturi Prievadas lauko']
    return []


def tikrinti_bash_sintakse():
    """bash -n visiems .sh failams (jei bash yra)."""
    klaidos = []
    try:
        subprocess.run(['bash', '--version'], capture_output=True, check=True)
    except Exception:
        return klaidos   # bash nėra -- praleidžiame
    for f in sorted(os.listdir(CIAPRASTAS)):
        if not f.endswith('.sh'):
            continue
        r = subprocess.run(['bash', '-n', os.path.join(CIAPRASTAS, f)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            klaidos.append('{0}: bash -n klaida: {1}'.format(f, r.stderr.strip()[:120]))
    return klaidos


def savitikra():
    viso = 0
    klaidos_viso = 0

    print("ATSTATYMO SISTEMOS SAVITIKRA")
    print("Aplankas: {0}".format(CIAPRASTAS))
    print("")

    # 1) failai + koduotė + saugumas
    print("--- 1) Failai, koduotė, saugumas ---")
    for f in sorted(os.listdir(CIAPRASTAS)):
        kelias = os.path.join(CIAPRASTAS, f)
        if f.endswith('.ps1'):
            klaidos, tekstas = tikrinti_ps1(kelias)
        elif f.endswith('.sh'):
            klaidos, tekstas = tikrinti_sh(kelias)
        elif f == 'savitikra.py':
            continue
        else:
            continue
        klaidos += tikrinti_sauguma(tekstas, f)
        klaidos += tikrinti_join_path(tekstas)
        viso += 1
        if klaidos:
            klaidos_viso += 1
            print("FAIL  {0}".format(f))
            for k in klaidos:
                print("        - {0}".format(k))
        else:
            print("PASS  {0}".format(f))

    # 2) ar yra visi tikimieji failai
    print("")
    print("--- 2) Ar yra visi reikalingi failai ---")
    for f in TIKIMI_FAILAI:
        viso += 1
        if os.path.exists(os.path.join(CIAPRASTAS, f)):
            print("PASS  {0}".format(f))
        else:
            klaidos_viso += 1
            print("FAIL  {0} (nėra)".format(f))

    # 3) dokumentai
    print("")
    print("--- 3) Dokumentų darna ---")
    klaidos = tikrinti_dokumentus()
    viso += 1
    if klaidos:
        klaidos_viso += 1
        print("FAIL  CLINE/ATSTATYMAS/")
        for k in klaidos:
            print("        - {0}".format(k))
    else:
        print("PASS  CLINE/ATSTATYMAS/ (01_TASKAS, registras, README)")

    # 4) 11 prievadų tikrintuvas
    print("")
    print("--- 4) 11 servisų tikrintuvas ---")
    klaidos = tikrinti_tikrintuvo_prievadus()
    viso += 1
    if klaidos:
        klaidos_viso += 1
        print("FAIL  patikrinti-servisus.ps1")
        for k in klaidos:
            print("        - {0}".format(k))
    else:
        print("PASS  patikrinti-servisus.ps1 tikrina visus 11 prievadų")

    # 5) bash sintaksė
    print("")
    print("--- 5) bash sintaksė ---")
    klaidos = tikrinti_bash_sintakse()
    viso += 1
    if klaidos:
        klaidos_viso += 1
        print("FAIL  .sh failai")
        for k in klaidos:
            print("        - {0}".format(k))
    else:
        print("PASS  visi .sh failai sintaksiškai teisingi")

    print("")
    print("{0}/{1} patikrų praėjo".format(viso - klaidos_viso, viso))
    return 0 if klaidos_viso == 0 else 1


def main(argv=None):
    return savitikra()


if __name__ == "__main__":
    sys.exit(main())

