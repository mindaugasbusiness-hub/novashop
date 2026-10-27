#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v5: neonine plytele sutraukta (64 px), paspaudus issiskleidzia (170 px).

M: „sita sutrauk, jo tokio didelio neturi buti“.

Naudojimas: python3 patch_neon_dancer_v5.py [--dry] [--file KELIAS]
"""
import argparse
import datetime
import os
import shutil
import sys

DEFAULT_PATH = "/opt/aukcionas/app.py"

HTML_OLD = '<div class="neon-dancer" id="neonDancer" aria-hidden="true">'
HTML_NEW = ('<div class="neon-dancer" id="neonDancer" role="button" tabindex="0" '
            'aria-label="Sokeja: sutraukti / isskleisti" '
            'onclick="this.classList.toggle(\'nd-open\')">')

CSS_ANCHOR = (".participants-panel:not(.reg-collapsed) .pp-reg-title::after"
              "{content:'  ▴ sutraukti';color:rgba(243,232,211,.55);}")

CSS_NEW = (CSS_ANCHOR + """
/* v5: plytele sutraukta, paspaudus issiskleidzia */
.neon-dancer{height:64px!important;cursor:pointer;pointer-events:auto;}
.neon-dancer.nd-open{height:170px!important;}
.neon-dancer .nd-tag::after{content:'  ▸';}
.neon-dancer.nd-open .nd-tag::after{content:'  ▾';}""")

MARK = ".neon-dancer{height:64px!important;"


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
    for name, old, new in (("HTML", HTML_OLD, HTML_NEW),
                           ("CSS", CSS_ANCHOR, CSS_NEW)):
        o, n = old.replace("\n", nl), new.replace("\n", nl)
        cnt = src.count(o)
        if cnt != 1:
            raise PatchError("%s ankeris rastas %d karta (turi buti 1). NIEKO NEIRASIAU."
                             % (name, cnt))
        src = src.replace(o, n, 1)
    return src, "patched"


def main(argv=None):
    ap = argparse.ArgumentParser(description="v5: sutraukta neonine plytele")
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
        print("JAU IDIEGTA (v5). NIEKO NEDARAU.")
        return 0
    if args.dry:
        print("DRY-RUN: butu +%d baitu, neirasoma." % (len(out) - len(src)))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-neonv5-%s" % (path, stamp)
    shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("OK: v5 idiegtas. Kopija: %s" % bak)
    print("Baitai: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
    print("Kitas zingsnis: systemctl restart aukcionas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
