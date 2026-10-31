#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N8N ĮRANKIŲ SAVITIKRA — patikrina tools/n8n/* failus prieš nusiunčiant į Windows.

Kodėl: 2026-10-26 sesijoje .cmd failai buvo SUGADINTI dėl netinkamos koduotės
(cmd.exe naudoja OEM kodų puslapį, o UTF-8 BOM laužo pirmą eilutę).
Čia tikrinama:
  1) .cmd -> ASCII (be diakritikų), CRLF, BE BOM, su @echo off ir exit /b
  2) .ps1 -> UTF-8 SU BOM (PowerShell 5.1 kitaip laužo diakritikus), CRLF
  3) subalansuoti { } ( ) [ ] skliaustai ir kabutės .ps1 failuose
  4) nėra vietos laikiklių (TODO, FIXME, "kelias iki projekto")
  5) nėra slaptažodžių/tokenų verčių (3 taisyklė)
  6) prievadai sutampa: 5678 serveris, 5679 brokeris, CLI 5690-5699
  7) kiekvienas .ps1 turi param() arba $PSScriptRoot ir grąžina exit kodą

Naudojimas:  python tools/n8n/savitikra.py [--aplankas KELIAS]
"""

import os
import re
import sys

CIAPRASTAS = os.path.dirname(os.path.abspath(__file__))

DRAUDZAMI_ZODZIAI = ["TODO", "FIXME", "placeholder", "kelias iki projekto"]
SLAPTU_SABLONAI = [r"password\s*=\s*['\"]?\S{6,}", r"secret\s*=\s*['\"]?\S{6,}",
                   r"api_?key\s*=\s*['\"]?\S{6,}", r"auth_?token\s*=\s*['\"]?\S{6,}"]

PRIEVADAI = {"serveris": 5678, "brokeris": 5679, "cli_nuo": 5690, "cli_iki": 5699}


def skaityti_baitus(kelias):
    with open(kelias, "rb") as f:
        return f.read()


def tikrinti_cmd(baitai):
    """.cmd taisyklės: ASCII, CRLF, be BOM."""
    klaidos = []
    if baitai.startswith(b"\xef\xbb\xbf"):
        klaidos.append("turi UTF-8 BOM (cmd.exe tai sulaužo)")
    try:
        tekstas = baitai.decode("ascii")
    except UnicodeDecodeError as e:
        klaidos.append("yra ne-ASCII simbolių (OEM kodų puslapis juos sulaužo): {0}".format(e))
        tekstas = baitai.decode("ascii", "replace")
    if b"\r\n" not in baitai and baitai:
        klaidos.append("neturi CRLF eilučių pabaigų")
    if b"\n" in baitai.replace(b"\r\n", b""):
        klaidos.append("turi LF-only eilučių")
    if "@echo off" not in tekstas:
        klaidos.append("neturi '@echo off'")
    if "exit /b" not in tekstas:
        klaidos.append("neturi 'exit /b' (grąžinimo kodo)")
    return klaidos


def tikrinti_ps1(baitai):
    """.ps1 taisyklės: UTF-8 su BOM, CRLF. Grąžina (klaidos, tekstas)."""
    klaidos = []
    turi_diakritiku = False
    try:
        tekstas = baitai.decode("utf-8")
        turi_diakritiku = any(ord(c) > 127 for c in tekstas)
    except UnicodeDecodeError as e:
        return ["nėra validus UTF-8: {0}".format(e)], ""
    if turi_diakritiku and not baitai.startswith(b"\xef\xbb\xbf"):
        klaidos.append("turi diakritikų, bet NETURI UTF-8 BOM -> PowerShell 5.1 juos sulaužys")
    tekstas = baitai.decode("utf-8-sig", "replace")
    if b"\r\n" not in baitai:
        klaidos.append("neturi CRLF eilučių pabaigų")
    if b"\n" in baitai.replace(b"\r\n", b""):
        klaidos.append("turi LF-only eilučių")
    return klaidos, tekstas


def tikrinti_skliaustus(tekstas):
    """Balanso tikrinimas: ignoruoja komentarus ir eilučių turinį."""
    atverti = {"{": 0, "(": 0, "[": 0}
    poros = {"}": "{", ")": "(", "]": "["}
    klaidos = []
    i, n, eilute = 0, len(tekstas), 1
    while i < n:
        c = tekstas[i]
        if c == "\n":
            eilute += 1
            i += 1
            continue
        if c == "#":
            while i < n and tekstas[i] != "\n":
                i += 1
            continue
        if c in "'\"":
            kabute = c
            i += 1
            while i < n:
                if tekstas[i] == "\n":
                    eilute += 1
                elif tekstas[i] == kabute:
                    if kabute == "'" and i + 1 < n and tekstas[i + 1] == "'":
                        i += 2
                        continue
                    if kabute == '"' and i + 1 < n and tekstas[i + 1] == '"':
                        i += 2
                        continue
                    break
                elif tekstas[i] == "`" and kabute == '"':
                    i += 2
                    continue
                i += 1
            if i >= n:
                klaidos.append("eilutė {0}: neuždaryta kabutė {1}".format(eilute, kabute))
                break
            i += 1
            continue
        if c in atverti:
            atverti[c] += 1
        elif c in poros:
            atverti[poros[c]] -= 1
            if atverti[poros[c]] < 0:
                klaidos.append("eilutė {0}: perteklinis '{1}'".format(eilute, c))
                atverti[poros[c]] = 0
        i += 1
    for skliaustas, kiekis in atverti.items():
        if kiekis != 0:
            klaidos.append("'{0}' balansas {1:+d}".format(skliaustas, kiekis))
    return klaidos




def tikrinti_turinys(tekstas, failo_vardas):
    """Vietos laikikliai, slaptažodžiai, prievadai, param/exit.

    Išimtys (sąmoningos):
      * n8n-konfig.ps1 yra dot-source biblioteka -> neturi ir NETURI turėti 'exit',
        nes kitaip nutrauktų jį pakvietusį skriptą.
      * .cmd failai neturi param()/$PSScriptRoot -- jie tik perduoda darbą .ps1 failui.
    """
    klaidos = []
    for z in DRAUDZAMI_ZODZIAI:
        if re.search(re.escape(z), tekstas, re.IGNORECASE):
            klaidos.append("rastas vietos laikiklis '{0}'".format(z))
    for sablonas in SLAPTU_SABLONAI:
        m = re.search(sablonas, tekstas, re.IGNORECASE)
        if m:
            klaidos.append("įtartina slapta reikšmė: {0}".format(m.group(0)[:50]))
    if failo_vardas == "n8n-konfig.ps1":
        for raktas, verte in PRIEVADAI.items():
            if str(verte) not in tekstas:
                klaidos.append("konfigūracijoje trūksta prievado {0} ({1})".format(raktas, verte))
    if failo_vardas.endswith(".ps1") and failo_vardas != "n8n-konfig.ps1":
        if "param(" not in tekstas and "$PSScriptRoot" not in tekstas:
            klaidos.append("neturi nei param(), nei $PSScriptRoot")
        if "exit " not in tekstas:
            klaidos.append("neturi 'exit' (grąžinimo kodo)")
    return klaidos



def savitikra(aplankas=None):
    aplankas = aplankas or CIAPRASTAS
    failai = sorted(f for f in os.listdir(aplankas) if f.endswith((".ps1", ".cmd")))
    if not failai:
        print("KLAIDA: aplanke {0} nėra .ps1/.cmd failų".format(aplankas))
        return 1

    viso = praejo = 0
    print("Tikrinamas aplankas: {0}".format(aplankas))
    print("")
    for f in failai:
        baitai = skaityti_baitus(os.path.join(aplankas, f))
        klaidos = []
        if f.endswith(".cmd"):
            klaidos += tikrinti_cmd(baitai)
            tekstas = baitai.decode("ascii", "replace")
        else:
            k, tekstas = tikrinti_ps1(baitai)
            klaidos += k
            if tekstas:
                klaidos += tikrinti_skliaustus(tekstas)
        if tekstas:
            klaidos += tikrinti_turinys(tekstas, f)

        viso += 1
        if not klaidos:
            praejo += 1
            print("PASS  {0:<24} ({1} B)".format(f, len(baitai)))
        else:
            print("FAIL  {0:<24} ({1} B)".format(f, len(baitai)))
            for k in klaidos:
                print("        - {0}".format(k))
    print("")
    print("{0}/{1} failų praėjo savitikrą".format(praejo, viso))
    return 0 if praejo == viso else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    aplankas = CIAPRASTAS
    if "--aplankas" in argv:
        i = argv.index("--aplankas")
        if len(argv) > i + 1:
            aplankas = argv[i + 1]
    print("N8N ĮRANKIŲ SAVITIKRA — kodų puslapis, CRLF/BOM, skliaustai, prievadai, slaptos reikšmės")
    print("")
    return savitikra(aplankas)


if __name__ == "__main__":
    sys.exit(main())

