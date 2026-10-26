#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IKELTI atsiustas dainas i F6 grotuva.
1) ikeliami failai is _NAUJOS i VPS /opt/aukcionas/desk_songs/NN.webm
2) VPS app.py: pridedami titulai (DESK_SONG_TITLES)
3) lokalus _desk_songs.py: pridedami irasai (CATALOG)
4) failai perkeliami i Desktop\\vid\\Muzika (kad liktu kaip saltinis)
5) patikra: /desk-songs/NN = 200

Numeracija prasideda nuo 36 (2..35 jau uzimti).
Saugiai: app.py ir _desk_songs.py - kopija, py_compile, klaidos atveju grazina.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DESKTOP = Path.home() / "Desktop"
STAGE = DESKTOP / "vid" / "Muzika" / "_NAUJOS"
MUZIKA = DESKTOP / "vid" / "Muzika"
LOG = DESKTOP / "vid" / "Muzika" / "_ikelimo_log.txt"
BUKLE = DESKTOP / "vid" / "Muzika" / "_ikelimo_bukle.json"
KEY = Path(r"C:\Users\M\CLINE\ssh\vps_cline")
IP = "root@5.175.171.113"
APP = "/opt/aukcionas/app.py"
SONGS_DIR = "/opt/aukcionas/desk_songs"
LOKALUS_KATALOGAS = DESKTOP / "pakeitimai 111" / "_desk_songs.py"
PRADZIA_NUO = 36
TS = time.strftime("%Y%m%d_%H%M%S")


def log(t: str) -> None:
    eil = time.strftime("%Y-%m-%d %H:%M:%S") + "  " + t
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(eil + "\n")
    print(eil, flush=True)


def ssh(cmd: str, timeout: int = 120) -> str:
    r = subprocess.run(["ssh", "-i", str(KEY), "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=15", IP, cmd],
                       capture_output=True, text=True, timeout=timeout)
    return ((r.stdout or "") + (r.stderr or "")).strip()


def bukle() -> dict:
    try:
        return json.loads(BUKLE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def issaugok(d: dict) -> None:
    BUKLE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def vps_uzimti() -> set:
    out = ssh("ls %s/ | tr '\\n' ' '" % SONGS_DIR)
    return set(int(m) for m in re.findall(r"(\d+)\.webm", out))


def ikelk(f: Path, n: int) -> bool:
    r = subprocess.run(["scp", "-i", str(KEY), "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=15", str(f),
                        "%s:%s/%d.webm" % (IP, SONGS_DIR, n)],
                       capture_output=True, text=True, timeout=400)
    if r.returncode != 0:
        log("    scp KLAIDA: " + ((r.stdout or "") + (r.stderr or ""))[:200])
        return False
    lok = hashlib.md5(f.read_bytes()).hexdigest()
    vps = ssh("md5sum %s/%d.webm" % (SONGS_DIR, n))
    if lok not in vps:
        log("    md5 NESUTAMPA: lok=%s / vps=%s" % (lok, vps[:60]))
        return False
    return True
def prideti_titulus(nauji: dict) -> bool:
    src = ssh("cat %s" % APP, timeout=180)
    if not src:
        log("  NEPAVYKO perskaityti VPS app.py")
        return False
    m = re.search(r"DESK_SONG_TITLES = \{(.*?)\n\}", src, re.S)
    if not m:
        log("  NEPAVYKO rasti DESK_SONG_TITLES")
        return False
    turimi = {}
    for mm in re.finditer(r"(\d+):\s*\"((?:[^\"\\]|\\.)*)\"", m.group(1)):
        turimi[int(mm.group(1))] = mm.group(2)
    visi = dict(turimi)
    visi.update(nauji)
    eilutes = "".join('    %d: "%s",\n' % (k, visi[k]) for k in sorted(visi))
    src2 = src[:m.start()] + "DESK_SONG_TITLES = {\n" + eilutes + "}" + src[m.end():]
    b64 = base64.b64encode(src2.encode("utf-8")).decode("ascii")
    prog = (
        "import base64,subprocess,sys\n"
        "P='%s'\n" % APP +
        "open(P,'wb').write(base64.b64decode('%s'))\n" % b64 +
        "r=subprocess.run([sys.executable,'-m','py_compile',P])\n"
        "print('py_compile rc', r.returncode)\n"
    )
    log("  VPS kopija: " + ssh("cp %s %s.bak-naujos-%s && echo OK" % (APP, APP, TS))[-20:])
    out = ssh("python3 -c '%s'" % prog, timeout=180)
    log("  VPS titulai: " + out[-160:].replace("\n", " "))
    if "py_compile rc 0" not in out:
        ssh("cp %s.bak-naujos-%s %s" % (APP, TS, APP))
        log("  GRAZINAU VPS app.py is kopijos")
        return False
    return True


def prideti_lokalu_kataloga(nauji: dict) -> bool:
    src = LOKALUS_KATALOGAS.read_text(encoding="utf-8")
    m = re.search(r"CATALOG: list\[tuple\[int, str, str\]\] = \[(.*?)\n\]", src, re.S)
    if not m:
        log("  NEPAVYKO rasti CATALOG")
        return False
    turimi = set(int(x) for x in re.findall(r"\((\d+),", m.group(1)))
    papildymas = ""
    for k in sorted(nauji):
        if k in turimi:
            continue
        title, needle = nauji[k]
        papildymas += '    (%d, "%s", "%s"),\n' % (k, title.replace('"', "'"), needle.replace('"', "'"))
    if not papildymas:
        log("  kataloge jau viskas")
        return True
    atsarginis = str(LOKALUS_KATALOGAS) + ".bak-naujos-" + TS
    shutil.copy2(LOKALUS_KATALOGAS, atsarginis)
    src2 = src[:m.end() - 1] + papildymas + src[m.end() - 1:]
    LOKALUS_KATALOGAS.write_text(src2, encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "py_compile", str(LOKALUS_KATALOGAS)],
                       capture_output=True, text=True)
    log("  lokalus katalogas py_compile rc = %d" % r.returncode)
    if r.returncode != 0:
        shutil.copy2(atsarginis, LOKALUS_KATALOGAS)
        log("  GRAZINAU lokalu kataloga")
        return False
    return True
def main() -> int:
    log("=== IKELIMAS PRADZIA ===")
    failai = sorted(STAGE.glob("*.webm"))
    if not failai:
        log("Nera ko kelti (tuscias _NAUJOS)")
        return 1
    b = bukle()
    uzimti = vps_uzimti()
    log("VPS jau turi numerius: %s" % sorted(uzimti))
    log("paruosta failu: %d" % len(failai))

    n = PRADZIA_NUO
    titulai, lok_katalogas = {}, {}
    ikelta = 0

    for f in failai:
        if b.get(f.name):
            log("  jau ikelta anksciau: %s (#%s)" % (f.name, b[f.name]))
            continue
        while n in uzimti:
            n += 1
        stem = f.stem
        if " - " in stem:
            artist, pav = stem.split(" - ", 1)
            rodomas = "%s \u2014 %s" % (artist.strip(), pav.strip())
        else:
            rodomas = stem
        log("  [%d] %s" % (n, f.name))
        if not ikelk(f, n):
            n += 1
            continue
        titulai[n] = rodomas
        lok_katalogas[n] = (rodomas, stem.upper())
        uzimti.add(n)
        b[f.name] = n
        ikelta += 1
        try:
            tikslas = MUZIKA / f.name
            if tikslas.exists():
                tikslas = MUZIKA / (f.stem + "_%d.webm" % n)
            shutil.move(str(f), str(tikslas))
        except Exception as e:
            log("    (nepavyko perkelti i Muzika: %r)" % e)
        issaugok(b)
        n += 1

    log("ikelta failu: %d" % ikelta)
    if not titulai:
        log("=== NIEKO NAUJO ===")
        return 0

    if prideti_titulus(titulai):
        log("VPS titulai prideti: %s" % sorted(titulai))
    else:
        log("VPS titulu prideti NEPAVYKO")
    if prideti_lokalu_kataloga(lok_katalogas):
        log("lokalus katalogas atnaujintas")
    else:
        log("lokalaus katalogo atnaujinti NEPAVYKO")

    log("--- perkraunu svetaine ---")
    log(ssh("systemctl restart aukcionas; sleep 6; systemctl is-active aukcionas", timeout=120))
    log("--- patikra (turi buti 200) ---")
    for k in sorted(titulai):
        r = ssh("curl -s -o /dev/null -w '%%{http_code}' http://127.0.0.1:8000/desk-songs/%d" % k)
        log("  /desk-songs/%d -> %s" % (k, r))
    log("=== BAIGTA ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())