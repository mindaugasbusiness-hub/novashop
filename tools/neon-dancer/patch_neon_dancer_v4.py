#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v4: kol registracija sutraukta — dalyviu sarasas aukstesnis (110 px).

v3 padare: forma sutraukta (46 px), sarasas matomas, bet tik 32 px aukscio.
v4: sutrauktoje busenoje sarasui 110 px, o atidarytoje — 32 px (kad forma tilptu).

Naudojimas: python3 patch_neon_dancer_v4.py [--dry] [--file KELIAS]
"""
import argparse
import datetime
import os
import shutil
import sys

DEFAULT_PATH = "/opt/aukcionas/app.py"

OLD = ("@media (max-height:620px){.neon-dancer{height:120px;}"
       ".participants-panel .pp-list{min-height:32px;}"
       ".participants-panel:not(.reg-collapsed) .neon-dancer{height:88px;}}")

NEW = ("@media (max-height:620px){.neon-dancer{height:120px;}"
       ".participants-panel.reg-collapsed .pp-list{min-height:110px;}"
       ".participants-panel:not(.reg-collapsed) .pp-list{min-height:32px;}"
       ".participants-panel:not(.reg-collapsed) .neon-dancer{height:88px;}}")

MARK = ".participants-panel.reg-collapsed .pp-list{min-height:110px;}"


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
    old_n, new_n = OLD.replace("\n", nl), NEW.replace("\n", nl)
    n = src.count(old_n)
    if n != 1:
        raise PatchError("v3 eilute rasta %d karta (turi buti 1). NIEKO NEIRASIAU." % n)
    return src.replace(old_n, new_n, 1), "patched"


def main(argv=None):
    ap = argparse.ArgumentParser(description="v4: aukstesnis dalyviu sarasas")
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
        print("JAU IDIEGTA (v4). NIEKO NEDARAU.")
        return 0
    if args.dry:
        print("DRY-RUN: butu +%d baitu, neirasoma." % (len(out) - len(src)))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-neonv4-%s" % (path, stamp)
    shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("OK: v4 idiegtas. Kopija: %s" % bak)
    print("Baitai: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
    print("Kitas zingsnis: systemctl restart aukcionas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
