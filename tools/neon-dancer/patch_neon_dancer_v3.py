#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3: registracija SUTRAUKTA pagal nutylejima + dalyviai matomi (auksciau).

M noras (2026-10-27): registracijos forma neturi buti iskart atidaryta —
matosi tik "1. REGISTRACIJA", o virsuje — aukciono dalyviai.

Svarbu: NIEKO netriname ir neperrasome esamu eiluciu:
  * dalyviu saraso pasleidimas (display:none !important) NELIEciamas —
    ji perrasome savo velesne taisykle (.pp-list{display:flex!important}),
    kuri deka eiliskumo laimi desktope, o mobilui (<=640 px) paliekame kaip buvo;
  * sutraukimo taisykles pridedamos globaliai (anksciau jos buvo tik <=640 px).

Naudojimas: python3 patch_neon_dancer_v3.py [--dry] [--file KELIAS]
"""
import argparse
import datetime
import os
import shutil
import sys

DEFAULT_PATH = "/opt/aukcionas/app.py"

# 1) JS: sutraukti ne tik telefone, bet visur
JS_OLD = ("    if(panel && window.innerWidth<=640 && !panel.dataset.regOpened) "
          "panel.classList.add('reg-collapsed');")
JS_NEW = ("    if(panel && !panel.dataset.regOpened) "
          "panel.classList.add('reg-collapsed');")

# 2) HTML: panelė jau gimsta sutraukta (kad neblyksteltų atidaryta forma)
HTML_OLD = '<div class="participants-panel" id="participantsPanel" aria-label="Dalyviai">'
HTML_NEW = '<div class="participants-panel reg-collapsed" id="participantsPanel" aria-label="Dalyviai">'

# 3) CSS: plyteles aukstis trumpame ekrane (kai forma atidaryta — mazesne)
CSS_OLD = ("@media (max-height:620px){.neon-dancer{height:88px;}"
           ".participants-panel .pp-list{min-height:32px;}}")
CSS_NEW = ("@media (max-height:620px){.neon-dancer{height:120px;}"
           ".participants-panel .pp-list{min-height:32px;}"
           ".participants-panel:not(.reg-collapsed) .neon-dancer{height:88px;}}")

# 4) CSS: pridedamos globalios sutraukimo ir saraso taisykles
TAIL_ANCHOR = "@media (prefers-reduced-motion:reduce){.neon-dancer{animation:none;}}"
TAIL_NEW = """@media (prefers-reduced-motion:reduce){.neon-dancer{animation:none;}}
/* SUTRAUKTA REGISTRACIJA + MATOMI DALYVIAI (2026-10-27, v3) */
.participants-panel .pp-list{display:flex!important;}
.participants-panel.reg-collapsed .pp-reg>*:not(.pp-reg-title){display:none!important;}
.participants-panel.reg-collapsed .pp-reg{padding-top:6px;border-top:0;}
.participants-panel .pp-reg-title{cursor:pointer;padding:5px 6px;border-radius:7px;background:rgba(255,179,71,.12);}
.participants-panel.reg-collapsed .pp-reg-title::after{content:'  ▾ atidaryti';color:#7dffa8;font-weight:700;}
.participants-panel:not(.reg-collapsed) .pp-reg-title::after{content:'  ▴ sutraukti';color:rgba(243,232,211,.55);}"""

MARK = "SUTRAUKTA REGISTRACIJA + MATOMI DALYVIAI"


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
    pairs = [
        ("JS (sutraukimas visur)", JS_OLD, JS_NEW),
        ("HTML (panelė sutraukta)", HTML_OLD, HTML_NEW),
        ("CSS (plytelė trumpame ekrane)", CSS_OLD, CSS_NEW),
        ("CSS (sutraukimo taisyklės)", TAIL_ANCHOR, TAIL_NEW),
    ]
    for name, old, new in pairs:
        old_n = old.replace("\n", nl)
        new_n = new.replace("\n", nl)
        n = src.count(old_n)
        if n != 1:
            raise PatchError("%s: ankeris rastas %d karta (turi buti 1). NIEKO NEIRASIAU." % (name, n))
        src = src.replace(old_n, new_n, 1)
    return src, "patched"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Neonine sokeja v3 (sutraukta registracija)")
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
        print("JAU IDIEGTA (v3). NIEKO NEDARAU.")
        return 0
    if args.dry:
        print("DRY-RUN: butu +%d baitu, neirasoma." % (len(out) - len(src)))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-neonv3-%s" % (path, stamp)
    shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("OK: v3 idiegtas. Kopija: %s" % bak)
    print("Baitai: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
    print("Kitas zingsnis: systemctl restart aukcionas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
