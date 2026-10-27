#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neonine sokeja (#12) — v2: matoma ir zemame ekrane.

Kodėl: M ekranas 1093x614, narsykles laukas ~540 px -> pataike i
@media (max-height:660px){display:none} ir plyteles nebuvo matyti.

v2 keicia TIK tas dvi eilutes (nieko netrina):
  - vietoj slepimo iki 660 px: iki 700 px plytele 110 px, iki 620 px — 88 px,
    o slepiama tik labai zemame (<=520 px);
  - tuo paciu metu dalyviu sarasui leidziama susitraukti (min-height 40 px / 32 px),
    kad plytele netilptu uz panelės ribu.

Naudojimas: tas pats kaip v1:
  python3 patch_neon_dancer_v2.py [--dry] [--file KELIAS]
"""
import argparse
import datetime
import os
import shutil
import sys

DEFAULT_PATH = "/opt/aukcionas/app.py"

OLD = """.participants-panel.registered .neon-dancer{height:172px;}
@media (max-height:760px){.neon-dancer{height:132px;}}
@media (max-height:660px){.neon-dancer{display:none!important;}}"""

NEW = """.participants-panel.registered .neon-dancer{height:150px;}
@media (max-height:760px){.neon-dancer{height:132px;}}
@media (max-height:700px){.neon-dancer{height:110px;}.participants-panel .pp-list{min-height:40px;}}
@media (max-height:620px){.neon-dancer{height:88px;}.participants-panel .pp-list{min-height:32px;}}
@media (max-height:520px){.neon-dancer{display:none!important;}}"""

MARK = "@media (max-height:620px){.neon-dancer{height:88px;}"


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
    old = OLD.replace("\n", nl)
    new = NEW.replace("\n", nl)
    n = src.count(old)
    if n != 1:
        raise PatchError("v1 blokas rastas %d karta (turi buti 1). NIEKO NEIRASIAU." % n)
    return src.replace(old, new, 1), "patched"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Neonine sokeja v2 (zemas ekranas)")
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
        print("JAU IDIEGTA (v2). NIEKO NEDARAU.")
        return 0
    if out == src:
        print("STOP: niekas nepasikeite")
        return 4
    if args.dry:
        print("DRY-RUN: butu +%d baitu, neirasoma." % (len(out) - len(src)))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-neonv2-%s" % (path, stamp)
    shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("OK: v2 idiegtas. Kopija: %s" % bak)
    print("Baitai: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
    print("Kitas zingsnis: systemctl restart aukcionas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
