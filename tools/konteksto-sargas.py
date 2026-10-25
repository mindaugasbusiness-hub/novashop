#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KONTEKSTO SARGAS
================
Tikslas: kad Cline sesija NIEKADA nebegautu raudonos klaidos del per dideles apimties.

Kodel raudona klaida ivyksta: pokalbio istorija (visi pranesimai + visi komandu
isvedimai + visi ilgi iplydymai) yra siunciama modeliui kiekviena zingsni. Kai
bendras kiekis virsija modelio "konteksto langa", sesija numeta raudona klaida ir
nebeatsako. Tai atsitinka NEPERSPEJUS - todel reikia is anksto matuoti ir perspeti.

Ka daro si priemone:
  check   - suranda Cline sesiju failus, suskaiciuoja kiekvienos sesijos apimti ir
            parodo, kiek % limito ji jau uzima. Perspeja DAR PRIES klaida.
  handoff - is 00_START_HERE.md + 02_DIENORASTIS.md + 04_TODO.md surinkia trumpa
            "pradzios promta" i viena faila. Kai sesija miršta, nauja sesija
            paleidziama per 1 minute ir iskart zino viska.

NIEKO NETRINA. Tik skaito ir (prireikus) iraso viena nauja faila.

Paleidimas:
  python konteksto-sargas.py check
  python konteksto-sargas.py check --budget 200000 --top 15
  python konteksto-sargas.py check --sessions-root "C:\\Users\\M\\.cline\\data\\sessions"
  python konteksto-sargas.py handoff
  python konteksto-sargas.py handoff --dir "C:\\Users\\M\\CLINE"
"""

import argparse
import os
import sys
import time

BYTES_PER_TOKEN = 4  # apytiksliai: 1 tokenas ~ 4 baitai JSON/teksto

# (riba, pavadinimas, ka daryti)
LEVELS = [
    (0.60, "OK", "Dirbk toliau. Checkpoint kas 5-10 zingsniu."),
    (0.80, "DEMESIO", "Uzbaik logiska dali, irasyk busena i 02_DIENORASTIS.md ir daryk commit."),
    (0.90, "PAVOJUS", "Nauju dideliu darbu NEPRADĖK. Irasyk busena, commit, atidaryk nauja sesija."),
    (9.99, "LIMITAS", "Sesija gali mirti bet kurią akimirka. Tik rasymas i failus."),
]


def human(n):
    return f"{n:,}".replace(",", " ")


def candidates():
    """Ieskome tipiniu Cline sesiju vietu (Windows, Linux, macOS)."""
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    out = []
    for editor in ("Code", "Cursor", "Windsurf", "VSCodium", "Code - Insiders"):
        out.append(
            os.path.join(appdata, editor, "User", "globalStorage",
                         "saoudrizwan.claude-dev", "tasks")
        )
    out.append(os.path.join(home, ".cline", "data", "sessions"))
    out.append(os.path.join(appdata, "cline", "data", "sessions"))
    return out


def dir_size(path):
    """Kiek baitu ir failu yra kataloge (rekursyviai)."""
    total = 0
    nfiles = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
                nfiles += 1
            except OSError:
                pass
    return total, nfiles


def rate(fraction):
    for limit, name, advice in LEVELS:
        if fraction < limit:
            return name, advice
    return LEVELS[-1][1], LEVELS[-1][2]


def read_lines(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return None


def cmd_check(args):
    roots = [args.sessions_root] if args.sessions_root else candidates()
    print("=== KONTEKSTO SARGAS ===")
    print("Limitas: {0} tokenu (~{1} baitu)".format(
        human(args.budget), human(args.budget * BYTES_PER_TOKEN)))

    rows = []
    checked = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        checked.append(root)
        try:
            names = sorted(os.listdir(root))
        except OSError:
            continue
        for name in names:
            path = os.path.join(root, name)
            if not os.path.isdir(path):
                continue
            size, nfiles = dir_size(path)
            if nfiles == 0:
                continue
            tokens = size // BYTES_PER_TOKEN
            rows.append({
                "name": name,
                "size": size,
                "files": nfiles,
                "tokens": tokens,
                "frac": tokens / float(args.budget),
                "mtime": os.path.getmtime(path),
            })

    if not checked:
        print("\nNERADAU nei vienos Cline sesiju vietos. Patikrinta:")
        for root in roots:
            print("   -", root)
        print("")
        print("Nurodyk rankiniu budu, pvz.:")
        print('   python konteksto-sargas.py check --sessions-root "C:\\Users\\M\\.cline\\data\\sessions"')
        return 0

    if not rows:
        print("\nKatalogai rasti, bet sesiju failu nera:")
        for root in checked:
            print("   -", root)
        return 0

    rows.sort(key=lambda r: r["frac"], reverse=True)
    print("Patikrinta:")
    for root in checked:
        print("   -", root)

    newest = max(rows, key=lambda r: r["mtime"])
    print("")
    print("{:<38} {:>6} {:>7} {:>11} {:>8}  {}".format(
        "SESIJA", "FAIL.", "MB", "~TOKENAI", "% LIM.", "BUSENA"))
    print("-" * 90)
    for r in rows[: args.top]:
        name, _advice = rate(r["frac"])
        mark = "  <-- paskutine dirbta" if r is newest else ""
        print("{:<38} {:>6} {:>7.1f} {:>11} {:>7.1f}%  {}{}".format(
            r["name"][:38], r["files"], r["size"] / 1048576.0,
            human(r["tokens"]), r["frac"] * 100, name, mark))

    worst = rows[0]
    name, advice = rate(worst["frac"])
    print("")
    print("Blogiausia sesija: {0} -> {1} ({2:.1f}% limito)".format(
        worst["name"], name, worst["frac"] * 100))
    print("SPRENDIMAS: " + advice)
    if worst["frac"] >= 0.80:
        print("Rekomenduojama dabar: python konteksto-sargas.py handoff")
    return 0


def cmd_handoff(args):
    base = args.dir
    docs = {
        "start": os.path.join(base, "00_START_HERE.md"),
        "diary": os.path.join(base, "02_DIENORASTIS.md"),
        "todo": os.path.join(base, "04_TODO.md"),
    }
    lines = []
    lines.append("# PRADZIOS PROMPTAS naujai Cline sesijai")
    lines.append("")
    lines.append("Sugeneruota: " + time.strftime("%Y-%m-%d %H:%M"))
    lines.append("Katalogo pagrindas: " + base)
    lines.append("")
    lines.append("## KA DARYTI")
    lines.append("Perskaityk zemiau esancias eilutes ir tesiam darba. Jei reikia detaliu -")
    lines.append("atidaryk failus: " + base + "\\00_START_HERE.md, 02_DIENORASTIS.md, 04_TODO.md.")
    lines.append("NIEKO netrink. Pirma atsakyk, kad supratai busena, ir pasakyk plana.")
    lines.append("")

    start = read_lines(docs["start"])
    if start:
        lines.append("## 00_START_HERE.md (pradzia, is viso {0} eil.)".format(len(start)))
        lines.append("```")
        lines.extend(start[: args.head])
        lines.append("```")
    else:
        lines.append("## 00_START_HERE.md - NERASTAS (" + docs["start"] + ")")
    lines.append("")

    diary = read_lines(docs["diary"])
    if diary:
        lines.append("## 02_DIENORASTIS.md (paskutines {0} eil. is {1})".format(
            args.tail, len(diary)))
        lines.append("```")
        lines.extend(diary[-args.tail:])
        lines.append("```")
    else:
        lines.append("## 02_DIENORASTIS.md - NERASTAS (" + docs["diary"] + ")")
    lines.append("")

    todo = read_lines(docs["todo"])
    if todo:
        lines.append("## 04_TODO.md (paskutines {0} eil. is {1})".format(
            args.tail, len(todo)))
        lines.append("```")
        lines.extend(todo[-args.tail:])
        lines.append("```")
    else:
        lines.append("## 04_TODO.md - NERASTAS (" + docs["todo"] + ")")
    lines.append("")
    lines.append("## KITAS ZINGSNIS")
    lines.append("<irasyk viena eilute, ka daryti toliau>")

    out_path = args.out or os.path.join(base, "PRADZIOS_PROMPTAS.txt")
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError as exc:
        print("NEPAVYKO irasyti: " + str(exc))
        return 1

    size = os.path.getsize(out_path)
    print("=== HANDOFF SUGENERUOTAS ===")
    print("Failas : " + out_path)
    print("Dydis  : {0} B (~{1} tokenu)".format(human(size), human(size // BYTES_PER_TOKEN)))
    print("Eilutes: {0}".format(len(lines)))
    print("")
    print("Dabar atidaryk nauja Cline sesija ir priciuosk sio failo turini.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Konteksto sargas - apsauga nuo per dideles Cline sesijos.")
    sub = parser.add_subparsers(dest="cmd")

    c = sub.add_parser("check", help="parodyti sesiju apimti ir perspejima")
    c.add_argument("--sessions-root", help="konkretus sesiju katalogas")
    c.add_argument("--budget", type=int, default=200000,
                   help="konteksto limitas tokenais (numatytas 200000)")
    c.add_argument("--top", type=int, default=15, help="kiek sesiju rodyti")
    c.set_defaults(func=cmd_check)

    h = sub.add_parser("handoff", help="sukurti pradzios promta naujai sesijai")
    h.add_argument("--dir", default=os.environ.get("CLINE_DIR", "C:\\Users\\M\\CLINE"),
                   help="kur yra 00_START_HERE.md ir kiti dokumentai")
    h.add_argument("--head", type=int, default=45,
                   help="kiek eiluciu imti is 00_START_HERE.md")
    h.add_argument("--tail", type=int, default=25,
                   help="kiek paskutiniu eiluciu imti is dienorascio")
    h.add_argument("--out", help="kur irasyti (numatytas <dir>\\PRADZIOS_PROMPTAS.txt)")
    h.set_defaults(func=cmd_handoff)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
