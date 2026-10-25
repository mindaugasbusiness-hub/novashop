#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULTO TAISYMAI — teisingi lietuviški užrašai, ženkliukai ir formatai valdymo pultui (:8790).

Kodėl: pulto ekrane yra daug netvarkos (detalus sąrašas — PULTO_TVARKYMAS.md):
  - mišrūs užrašai vienam ir tam pačiam dalykui: "RODOMAS", "NE", "active", "is-active",
    "cache", "uploads", "[icy]", "True"
  - trūksta lietuviškų diakritikų: is, uzimta, failu, aplanku, dainu, ivykiu, ZINIOS
  - skaičiai su tašku (1.76 MB, 18.9 s, 7.8G) lietuviškame tekste
  - data/laikas be laiko juostos, o žurnaluose kitas laikas nei antraštėje
  - Python True/False rodomas vietoj TAIP/NE

Šis failas duoda paruoštas funkcijas, kad pulto kodas nerašytų tekstų rankomis.

Patikra:  python pultas-taisymai.py --self-test
"""

import re
import sys

# --- 1) BŪSENŲ ŽENKLIUKAI -------------------------------------------------
ZENKLAS_VEIKIA = "VEIKIA"
ZENKLAS_NEVEIKIA = "NEVEIKIA"
ZENKLAS_AKTYVUS = "AKTYVUS"
ZENKLAS_PASENES = "PASENĘS"
ZENKLAS_SVIEZIAS = "ŠVIEŽIAS"


def zenklas(veikia, aktyvus=False):
    """Vieningas būsenos ženkliukas. Niekada 'RODOMAS' / 'active' / 'is-active'."""
    if aktyvus:
        return ZENKLAS_AKTYVUS
    return ZENKLAS_VEIKIA if veikia else ZENKLAS_NEVEIKIA


def taip_ne(verte):
    """Python True/False -> TAIP/NE (pultas dabar rodo 'True')."""
    return "TAIP" if verte else "NE"


# --- 2) SKAIČIAI IR VIENETAI ---------------------------------------------
def sk(skaicius, po_kablelio=0):
    """Lietuviškas formatas: 1000 -> '1 000', 1.76 -> '1,76'."""
    fmt = "{:,.{p}f}".format(float(skaicius), p=po_kablelio)
    return fmt.replace(",", "\u00a0").replace(".", ",")


def dydis(baitu):
    """10240 -> '10 KB', 1845000 -> '1,76 MB' (pultas dabar rodo '0.01 MB')."""
    baitu = float(baitu)
    if baitu < 1024:
        return "{0} B".format(sk(baitu, 0))
    if baitu < 1024 * 1024:
        return "{0} KB".format(sk(baitu / 1024.0, 0))
    return "{0} MB".format(sk(baitu / (1024.0 * 1024.0), 2))


def proc_uzimta(viso_gb, laisva_gb):
    """(14, 7.8) -> '44 %' (pultas dabar rodo '43%' ir sumaišo laisvą su užimta)."""
    viso_gb = float(viso_gb)
    if viso_gb <= 0:
        return "0 %"
    uzimta = (viso_gb - float(laisva_gb)) / viso_gb * 100.0
    return sk(round(uzimta), 0) + " %"


def disko_eilute(viso_gb, laisva_gb):
    """Viena aiški eilutė vietoj 'laisva 7.8G is 14G (43% uzimta)'."""
    return "laisva {0} GB iš {1} GB (užimta {2})".format(
        sk(laisva_gb, 1), sk(viso_gb, 0), proc_uzimta(viso_gb, laisva_gb))


# --- 3) TEKSTO VALYMAS ----------------------------------------------------
def isvalyti_icy(tekstas):
    """'DMX - X GON [icy]' -> 'DMX - X GON' (pultas dabar rodo '[icy]')."""
    return re.sub(r"\s*\[[a-z]+\]\s*$", "", (tekstas or "").strip())


def amzius(h, riba=20):
    """(24.5) -> 'PASENĘS (24,5 h)' — pultas senas kopijas rodo kaip 'RODOMAS'."""
    if h is None:
        return "NĖRA DUOMENŲ"
    if h >= riba:
        return "{0} ({1} h)".format(ZENKLAS_PASENES, sk(h, 1))
    return "{0} ({1} h)".format(ZENKLAS_SVIEZIAS, sk(h, 1))


def laikas(tekstas, juosta):
    """'09:50:01' -> '09:50:01 (VPS)'.

    Pultas dabar rodo 3 skirtingus laikus be jokios nuorodos: 02:54 antraštėje,
    08:04 'paskutinis', 09:40-09:50 VPS žurnaluose.
    """
    return "{0} ({1})".format((tekstas or "").strip(), juosta)


# --- 4) IŠDĖSTYMO PATAISYMAS (tuščios skylės D/E/F sekcijose) -------------
CSS = """/* Pulto tinklelio pataisymas: kad neliktų tuščių skylių (D, E, F sekcijos) */
.pulto-tinklelas {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-items: start;     /* svarbiausia: kortelė netempiama iki eilutės aukščio */
  align-content: start;
}
.pulto-kortele { align-self: start; }
/* jei liko nelyginis kortelių skaičius - paskutinė eina per visą plotį */
.pulto-tinklelas > .pulto-kortele:last-child:nth-child(odd) { grid-column: 1 / -1; }
"""


# --- 5) TIKSLŪS TEKSTŲ PATAISYMAI (senas -> naujas) -----------------------
PATAISYMAI = [
    ("Servisai rodomas", "Servisai veikia"),
    ("RODOMAS: ", "VEIKIA: "),
    ("NE: ", "NEVEIKIA: "),
    ("(iš 6 viso)", "(iš viso: 6)"),
    ("daina negroja", "daina: negroja"),
    ("botu: ", "botų: "),
    ("failu: ", "failų: "),
    ("aplanku viso: ", "aplankų iš viso: "),
    ("dainu: ", "dainų: "),
    ("ivykiu: ", "įvykių: "),
    ("07_ZINIOS.md", "07_ŽINIOS.md"),
    ("PRANESIMU_LOG.txt", "PRANEŠIMŲ_LOG.txt"),
    ("BUDEJIMAS_LOG.txt", "BUDĖJIMO_LOG.txt"),
    ("is-active", "aktyvus"),
    ("(cache ", "(podėlis: "),
    ("modelis=", "modelis: "),
    ("uploads=", "įkėlimai: "),
    ("= True", ": TAIP"),
    ("= False", ": NE"),
    (" is 14G ", " iš 14 GB "),
    ("(43% uzimta)", "(užimta 44 %)"),
]


def pataisyk(tekstas):
    """Pritaiko visus teksto pataisymus."""
    for senas, naujas in PATAISYMAI:
        tekstas = tekstas.replace(senas, naujas)
    return tekstas


# --- 6) SAVITIKRA ---------------------------------------------------------
def self_test():
    atvejai = [
        ("zenklas(True)", zenklas(True), ZENKLAS_VEIKIA),
        ("zenklas(False)", zenklas(False), ZENKLAS_NEVEIKIA),
        ("zenklas(True, aktyvus=True)", zenklas(True, aktyvus=True), ZENKLAS_AKTYVUS),
        ("taip_ne(True)", taip_ne(True), "TAIP"),
        ("taip_ne(False)", taip_ne(False), "NE"),
        ("sk(1000)", sk(1000), "1\u00a0000"),
        ("sk(1.76, 2)", sk(1.76, 2), "1,76"),
        ("sk(18.9, 1)", sk(18.9, 1), "18,9"),
        ("dydis(512)", dydis(512), "512 B"),
        ("dydis(10240)", dydis(10240), "10 KB"),
        ("dydis(1845000)", dydis(1845000), "1,76 MB"),
        ("proc_uzimta(14, 7.8)", proc_uzimta(14, 7.8), "44 %"),
        ("disko_eilute(14, 7.8)", disko_eilute(14, 7.8),
         "laisva 7,8 GB iš 14 GB (užimta 44 %)"),
        ("isvalyti_icy('DMX - X GON [icy]')", isvalyti_icy("DMX - X GON [icy]"),
         "DMX - X GON"),
        ("isvalyti_icy('Be jokio zenklo')", isvalyti_icy("Be jokio zenklo"),
         "Be jokio zenklo"),
        ("amzius(24.5)", amzius(24.5), "PASENĘS (24,5 h)"),
        ("amzius(3.2)", amzius(3.2), "ŠVIEŽIAS (3,2 h)"),
        ("laikas('09:50:01', 'VPS')", laikas("09:50:01", "VPS"), "09:50:01 (VPS)"),
        ("pataisyk('RODOMAS: 5 NE: 1')", pataisyk("RODOMAS: 5 NE: 1"),
         "VEIKIA: 5 NEVEIKIA: 1"),
        ("pataisyk('failu: 17')", pataisyk("failu: 17"), "failų: 17"),
        ("pataisyk('= True')", pataisyk("= True"), ": TAIP"),
        ("pataisyk('(cache 18.9 s)')", pataisyk("(cache 18.9 s)"), "(podėlis: 18.9 s)"),
    ]
    klaidos = 0
    for pavadinimas, gauta, tiketa in atvejai:
        ok = gauta == tiketa
        if not ok:
            klaidos += 1
        print("{0}  {1:<38} gauta={2!r:<30} tiketa={3!r}".format(
            "PASS" if ok else "FAIL", pavadinimas, gauta, tiketa))
    print("")
    print("{0}/{1} patikrų praėjo".format(len(atvejai) - klaidos, len(atvejai)))
    return 1 if klaidos else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv or "-t" in argv:
        return self_test()
    if "--css" in argv:
        print(CSS)
        return 0
    if "--pataisymai" in argv:
        for senas, naujas in PATAISYMAI:
            print("{0!r} -> {1!r}".format(senas, naujas))
        return 0
    print(__doc__)
    print("Komandos: --self-test | --css | --pataisymai")
    return 0


if __name__ == "__main__":
    sys.exit(main())
