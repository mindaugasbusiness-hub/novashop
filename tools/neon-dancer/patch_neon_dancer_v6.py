#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6: dalyviu sarasas — ribotas aukstis (110 px) su slinkimu, rodoma iki 60 vardu.

Priezastis: ijungus sarasa paaiskejo, kad jame 500 mokymosi botu -> panele
issipute iki 3375 px ir plytele nusistume uz ekrano.

Naudojimas: python3 patch_neon_dancer_v6.py [--dry] [--file KELIAS]
"""
import argparse
import datetime
import os
import shutil
import sys

DEFAULT_PATH = "/opt/aukcionas/app.py"

ANCHOR = ".neon-dancer.nd-open .nd-tag::after{content:'  ▾';}"
NEW = ANCHOR + """
/* v6: dalyviu sarasas — fiksuotas aukstis + slinkimas, rodoma iki 60 vardu */
.participants-panel .pp-list{max-height:110px!important;overflow-y:auto!important;flex:0 1 auto!important;}
.participants-panel .pp-name:nth-child(n+61){display:none!important;}"""

MARK = ".participants-panel .pp-name:nth-child(n+61)"


class PatchError(Exception):
    pass


def _nl_of(src):
    crlf = src.count("\r\n")
    lf = src.count("\n") - crlf
    return "\r\n" if crlf >= lf else "\n"


def apply_patch(src):
    if MARK in src:
        return src, "already"
    nl = _nl_of(src)
    o, n = ANCHOR.replace("\n", nl), NEW.replace("\n", nl)
    cnt = src.count(o)
    if cnt != 1:
        raise PatchError("CSS ankeris rastas %d karta (turi buti 1). NIEKO NEIRASIAU." % cnt)
    return src.replace(o, n, 1), "patched"


def main(argv=None):
    ap = argparse.ArgumentParser(description="v6: dalyviu sarasas 110px su slinkimu")
    ap.add_argument("--file", default=DEFAULT_PATH)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    path = args.file
    if not os.path.isfile(path):
        print("STOP: nera failo %s" % path)
        return 5
    with open(path, "r", encoding="utf-8", newline="") as fh:
        src = fh.read()
    try:
        out, status = apply_patch(src)
    except PatchError as exc:
        print("STOP: %s" % exc)
        return 2
    if status == "already":
        print("JAU IDIEGTA (v6). NIEKO NEDARAU.")
        return 0
    if args.dry:
        print("DRY-RUN: butu +%d baitu, neirasoma." % (len(out) - len(src)))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-neonv6-%s" % (path, stamp)
    shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("OK: v6 idiegtas. Kopija: %s" % bak)
    print("Baitai: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
    print("Kitas zingsnis: systemctl restart aukcionas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
