#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Savitikra: neonines sokejos (#12) idejimas i app.py — be serverio, ant KOPIJOS.

Naudojimas:
  python3 savitikra.py [kelias iki app.py kopijos]

Jei kelias nenurodytas, imama /tmp/neonbase/app_now.py (ten, kur buvo istraukta
naujausia serverio app.py versija). Originalus failas NELIECIAMAS — viskas daroma
laikiname kataloge.

Rezultatas: kiekvienas patikrinimas atspausdinamas PASS/FAIL, gale santrauka.
Isėjimo kodas: 0 = visi PASS, 1 = yra FAIL.
"""
import importlib.util
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE = "/tmp/neonbase/app_now.py"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail else ""))
    return bool(ok)


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "patch_neon_dancer", os.path.join(HERE, "patch_neon_dancer.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ids_in(src):
    return re.findall(r'\bid="([^"]+)"', src)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    base_path = argv[0] if argv else DEFAULT_BASE
    if not os.path.isfile(base_path):
        print("STOP: nera bazines kopijos %s" % base_path)
        print("Istravimas:  git show origin/cline/ejzcxn55:_app_now.py > %s" % base_path)
        return 2

    tool = load_tool()
    base = open(base_path, "r", encoding="utf-8", newline="").read()

    print("=== 1) ANKERIAI (bazeje) ===")
    check("CSS ankeris rastas 1 karta", base.count(tool.CSS_ANCHOR) == 1,
          "x%d" % base.count(tool.CSS_ANCHOR))
    check("HTML ankeris rastas 1 karta", base.count(tool.HTML_ANCHOR) == 1,
          "x%d" % base.count(tool.HTML_ANCHOR))
    check("zenklas 'neon-dancer' bazeje dar nebuvo", tool.MARKER not in base)

    out, status = tool.apply_patch(base)
    print("=== 2) IDEJIMAS ===")
    check("busena = patched", status == tool.PATCHED, status)
    check("tekstas pasikeite", out != base, "+%d baitu" % (len(out) - len(base)))

    added = out.count("\n") - base.count("\n")
    expected = tool.NEON_CSS.count("\n") + 1 + tool.NEON_HTML.count("\n") + 1
    check("pridetu eiluciu skaicius sutampa", added == expected,
          "prideta %d, tiketasi %d" % (added, expected))

    bare_lf_out = out.count("\n") - out.count("\r\n")
    check("CRLF islaikyti (nera vienisu LF)", bare_lf_out == 0, "vienisu LF: %d" % bare_lf_out)

    print("=== 3) HTML ===")
    check('class="neon-dancer" lygiai 1', out.count('class="neon-dancer"') == 1,
          "x%d" % out.count('class="neon-dancer"'))
    check('id="neonDancer" lygiai 1', out.count('id="neonDancer"') == 1)
    check("video src /photos/dance_club_12.mp4 lygiai 1",
          out.count('src="/photos/dance_club_12.mp4"') == 1)
    check("video atidaryta ir uzdaryta po 1 karta",
          out.count("<video") == base.count("<video") + 1
          and out.count("</video>") == base.count("</video>") + 1)
    check("autoplay muted loop playsinline yra",
          'autoplay muted loop playsinline preload="auto"' in tool.NEON_HTML)

    i_join = out.find('id="joinForm"')
    i_neon = out.find('id="neonDancer"')
    i_done = out.find('id="ppDone"')
    check("vieta: po #joinForm ir pries #ppDone", 0 < i_join < i_neon < i_done,
          "joinForm=%d neon=%d ppDone=%d" % (i_join, i_neon, i_done))

    print("=== 4) CSS ===")
    check("selektorius .neon-dancer{ yra 1", out.count(".neon-dancer{position") == 1)
    check("keyframes neonDancerGlow yra 1", out.count("@keyframes neonDancerGlow") == 1)
    check("mobiliame (max-width:640px) paslepta",
          "@media (max-width:640px){.neon-dancer{display:none!important;}}" in tool.NEON_CSS)
    check("zemame ekrane (max-height:660px) paslepta",
          "@media (max-height:660px){.neon-dancer{display:none!important;}}" in tool.NEON_CSS)
    check("prefers-reduced-motion atsizvelgta",
          "prefers-reduced-motion:reduce){.neon-dancer{animation:none;}}" in tool.NEON_CSS)
    check("CSS skliaustai subalansuoti",
          tool.NEON_CSS.count("{") == tool.NEON_CSS.count("}"),
          "atidaryta %d, uzdaryta %d" % (tool.NEON_CSS.count("{"), tool.NEON_CSS.count("}")))
    i_panel = out.find(".participants-panel{")
    i_css = out.find(".neon-dancer{position")
    check("CSS idetas po .participants-panel", 0 < i_panel < i_css)

    print("=== 5) SAUGUMAS ===")
    check("idetame kode nera <script", "<script" not in tool.NEON_HTML.lower())
    check("idetame kode nera on*= (inline JS)",
          not re.search(r"\son[a-z]+\s*=", tool.NEON_HTML, re.I))
    before_ids = ids_in(base)
    after_ids = ids_in(out)
    before_dup = set(i for i in before_ids if before_ids.count(i) > 1)
    after_dup = set(i for i in after_ids if after_ids.count(i) > 1)
    new_dups = sorted(after_dup - before_dup)
    check("nauju dubliuotu id neatsirado", not new_dups, "nauji: %s" % (new_dups or "nera"))

    print("=== 6) PAKARTOTINIS PALEIDIMAS (idempotencija) ===")
    out2, status2 = tool.apply_patch(out)
    check("antra karta: busena = already", status2 == tool.ALREADY, status2)
    check("antra karta: tekstas nepakito", out2 == out)

    print("=== 7) FAILO FORMATAS ===")
    try:
        compile(out, "app_after_patch.py", "exec")
        ok_py, why = True, ""
    except SyntaxError as exc:
        ok_py, why = False, str(exc)
    check("po pakeitimo vis dar galiojantis Python failas", ok_py, why)

    print("=== 8) KOMANDINE EILUTE (tikra eiga laikiname kataloge) ===")
    tmp = tempfile.mkdtemp(prefix="neon-")
    try:
        work = os.path.join(tmp, "app.py")
        shutil.copyfile(base_path, work)

        rc = tool.main(["--file", work, "--dry"])
        check("--dry grazina 0", rc == 0, "rc=%d" % rc)
        check("--dry NIEKO neirase",
              open(work, encoding="utf-8", newline="").read() == base)

        rc = tool.main(["--file", work])
        check("irasymas grazina 0", rc == 0, "rc=%d" % rc)
        check("failas tikrai pasikeite",
              open(work, encoding="utf-8", newline="").read() == out)

        baks = sorted(f for f in os.listdir(tmp) if f.startswith("app.py.bak-neon-"))
        check("sukurta .bak kopija", len(baks) == 1, ", ".join(baks) or "nera")
        if baks:
            bak_txt = open(os.path.join(tmp, baks[0]), encoding="utf-8", newline="").read()
            check(".bak turinys = originalas", bak_txt == base)

        rc = tool.main(["--file", work])
        check("antras paleidimas: rc=0 ir nieko nekeicia",
              rc == 0 and open(work, encoding="utf-8", newline="").read() == out,
              "rc=%d" % rc)

        missing = tool.main(["--file", os.path.join(tmp, "nera.py")])
        check("nera failo -> rc=5", missing == 5, "rc=%d" % missing)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== 9) NEIGIAMAS TESTAS (sugadintas ankeris) ===")
    broken = base.replace(tool.CSS_ANCHOR, ".participants-panel .pp-done-ZORGE{x:y;}", 1)
    caught = False
    try:
        tool.apply_patch(broken)
    except tool.PatchError:
        caught = True
    check("netinkamas ankeris sustabdo darba (PatchError)", caught)

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print()
    print("SANTRAUKA: %d/%d PASS" % (passed, total))
    if passed != total:
        print("NEPAVYKO:")
        for name, ok, detail in results:
            if not ok:
                print("  - %s %s" % (name, detail))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
