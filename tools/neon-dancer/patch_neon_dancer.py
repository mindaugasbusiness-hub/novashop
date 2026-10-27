#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neonine sokeja (#12) — penktadienioaukcionas.lt kaireje puseje, po registracijos formos.

Tikslas: i app.py ideti nedidele neonine video plytele su /photos/dance_club_12.mp4,
kuri rodoma KAIRIAJAME dalyviu panelyje (participants-panel), PO registracijos formos
(po #joinForm), pries "pp-done" bloka.

Saugumas (pagal 03_TAISYKLES.md 1 taisykle):
  * nieko netrina ir neperraso be kopijos — pries irasyma daroma .bak kopija su data/laiku;
  * jei ieskomo teksto yra ne 1 karta — STABDO darba ir NIEKO neraso;
  * jei jau idiegta — pranesama ir nieko nedaroma (galima leisti daug karta);
  * CRLF (Windows) eiluciu galai islaikomi tokie, kokie buvo faile.

Naudojimas:
  python3 patch_neon_dancer.py                    # tikrina ir iraso i /opt/aukcionas/app.py
  python3 patch_neon_dancer.py --dry              # tik tikrina, nieko neraso
  python3 patch_neon_dancer.py --file /tmp/x.py   # kitas failas (testavimui)

Isėjimo kodai: 0 = gerai (irasyta arba jau buvo), 2 = netinkamas failas/ankeriai,
               4 = niekas nepasikeite, 5 = trūksta failo.
"""
import argparse
import datetime
import os
import shutil
import sys

DEFAULT_PATH = "/opt/aukcionas/app.py"

# --- 1) CSS ankeris: viena eilute, kuri faile yra TIK 1 karta ---
CSS_ANCHOR = (
    ".participants-panel .pp-done{font-size:12px;color:#7dffa8;"
    "padding:6px 0 2px;display:flex;flex-direction:column;gap:6px;}"
)

# --- 2) HTML ankeris: "pp-done" bloko pradzia (TIK 1 karta) ---
HTML_ANCHOR = '  <div class="pp-done" id="ppDone" style="display:none;">'

MARKER = 'class="neon-dancer"'

PATCHED = "patched"
ALREADY = "already"

NEON_CSS = """/* NEON SOKEJA (2026-10-27): #12 /photos/dance_club_12.mp4 — kaireje, po registracijos formos */
.neon-dancer{position:relative;flex:0 0 auto;width:100%;height:160px;border-radius:10px;overflow:hidden;
  border:1px solid rgba(120,220,255,.55);background:#04070c;isolation:isolate;
  box-shadow:0 0 0 1px rgba(120,220,255,.16),0 0 12px rgba(0,190,255,.30),inset 0 0 20px rgba(0,120,255,.22);
  animation:neonDancerGlow 3.4s ease-in-out infinite alternate;}
.neon-dancer .nd-video{width:100%;height:100%;object-fit:cover;object-position:center 34%;display:block;pointer-events:none;}
.neon-dancer::after{content:'';position:absolute;inset:0;z-index:1;pointer-events:none;border-radius:9px;
  background:radial-gradient(120% 90% at 50% 0%,rgba(0,190,255,.20),transparent 62%),
             linear-gradient(180deg,rgba(0,0,0,0) 52%,rgba(0,0,0,.62) 100%);}
.neon-dancer .nd-tag{position:absolute;left:7px;bottom:6px;z-index:2;pointer-events:none;
  font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;
  color:#bff3ff;text-shadow:0 0 7px rgba(0,200,255,.95),0 1px 2px #000;opacity:.92;}
@keyframes neonDancerGlow{
  from{border-color:rgba(120,220,255,.42);box-shadow:0 0 0 1px rgba(120,220,255,.14),0 0 9px rgba(0,190,255,.24),inset 0 0 16px rgba(0,120,255,.18);}
  to{border-color:rgba(195,245,255,.85);box-shadow:0 0 0 1px rgba(195,245,255,.32),0 0 22px rgba(0,200,255,.55),inset 0 0 26px rgba(0,140,255,.30);}
}
.participants-panel.registered .neon-dancer{height:172px;}
@media (max-height:760px){.neon-dancer{height:132px;}}
@media (max-height:660px){.neon-dancer{display:none!important;}}
@media (max-width:640px){.neon-dancer{display:none!important;}}
@media (prefers-reduced-motion:reduce){.neon-dancer{animation:none;}}"""

NEON_HTML = """  <!-- NEON SOKEJA (2026-10-27): #12 — kaireje, po registracijos formos -->
  <div class="neon-dancer" id="neonDancer" aria-hidden="true">
    <video class="nd-video" src="/photos/dance_club_12.mp4" autoplay muted loop playsinline preload="auto" aria-hidden="true"></video>
    <span class="nd-tag">neon</span>
  </div>"""


class PatchError(Exception):
    """Ankeris nerastas arba rastas ne viena karta — nieko nerasome."""


def _nl_of(src):
    """Grazina vyraujanti eiluciu galo zyma: CRLF arba LF."""
    crlf = src.count("\r\n")
    lf = src.count("\n") - crlf
    return "\r\n" if crlf >= lf else "\n"


def apply_patch(src):
    """Grazina (naujas_tekstas, busena). Neko neraso i diska.

    busena: PATCHED — ideta; ALREADY — jau buvo.
    Kelia PatchError, jei ankeris netinkamas.
    """
    if MARKER in src:
        return src, ALREADY

    for name, anchor in (("CSS", CSS_ANCHOR), ("HTML", HTML_ANCHOR)):
        n = src.count(anchor)
        if n != 1:
            raise PatchError(
                "%s ankeris rastas %d karta (turi buti 1). NIEKO NEIRASIAU.\n"
                "Ieskota: %s" % (name, n, anchor[:90])
            )

    nl = _nl_of(src)
    css_block = NEON_CSS.replace("\n", nl)
    html_block = NEON_HTML.replace("\n", nl)

    out = src.replace(CSS_ANCHOR, CSS_ANCHOR + nl + css_block, 1)
    out = out.replace(HTML_ANCHOR, html_block + nl + HTML_ANCHOR, 1)
    return out, PATCHED


def main(argv=None):
    ap = argparse.ArgumentParser(description="Neonine sokeja (#12) i app.py")
    ap.add_argument("--file", default=DEFAULT_PATH, help="kelias iki app.py (default %s)" % DEFAULT_PATH)
    ap.add_argument("--dry", action="store_true", help="tik patikrinti, nieko nerasyti")
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

    if status == ALREADY:
        print("JAU IDIEGTA: '%s' jau yra faile. NIEKO NEDARAU." % MARKER)
        return 0

    if out == src:
        print("STOP: niekas nepasikeite")
        return 4

    if args.dry:
        print("DRY-RUN: pakeitimai paruosti, bet NEIRASYTI.")
        print("Baitai butu: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
        if "\r\n" in src:
            print("Eiluciu galai: CRLF (butu islaikyti)")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = "%s.bak-neon-%s" % (path, stamp)
    shutil.copyfile(path, backup)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("OK: ideta neonine sokeja (#12).")
    print("Kopija pries irasyma: %s" % backup)
    print("Baitai: %d -> %d (+%d)" % (len(src), len(out), len(out) - len(src)))
    print("Kitas zingsnis: systemctl restart aukcionas")
    print("Grazinimas atgal: cp '%s' '%s'" % (backup, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
