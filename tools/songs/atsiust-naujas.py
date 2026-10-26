#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATSISIUSTI DAINAS i F6 grotuva.
Siuncia M noru sarasa (Shazam) + patinkancios_muzikos_notepad.txt i
Desktop\\vid\\Muzika\\_NAUJOS. Po to atskiras zingsnis ikels i VPS.

Paleidziama fone:  python -X utf8 _atsiust_naujas.py
Eiga rasyta i:     Desktop\\vid\\Muzika\\_atsiuntimo_log.txt
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

DESKTOP = Path.home() / "Desktop"
STAGE = DESKTOP / "vid" / "Muzika" / "_NAUJOS"
LOG = DESKTOP / "vid" / "Muzika" / "_atsiuntimo_log.txt"
STAGE.mkdir(parents=True, exist_ok=True)

# (atlikėjas, pavadinimas, ar rodomas grotuve pavadinimas)
NORAI: list[tuple[str, str]] = [
    ("Bernužėliai", "Maldauju Pasilik"),
    ("Samanta Tina & Rassell", "Esi Man Klāt"),
    ("Chico & Qatoshi", "Mamma Mia"),
    ("Qi Yuan", "Love You Like a Love Song"),
    ("Naarly", "LIFE"),
    ("Linkin Park", "Don't Stay"),
    ("Zairi Torrez", "Progressive World 2Qimic Remix"),
    ("Linkin Park", "One Step Closer"),
    ("Dj Dark & Amélie", "Voyage Voyage"),
    ("Dovi Mi", "Aukščiau Nei Kyla Lėktuvai"),
    ("YAKTAK", "LaLaLa"),
    ("Jeremy Hongslo", "Last Goodbye"),
    ("Imael Angel", "BAD TIMES Long Version"),
    ("Olivier Chalopin", "Dernière danse"),
    ("Ofenbach", "Be Mine"),
    ("Whigfield", "Saturday Night Nite Mix"),
    ("Zucchero", "Baila Sexy Thing"),
    ("Daniel Gros", "Shorty Joe Nick da Cruz Bill Wilson Remix"),
    ("Extazik", "How 2 Dance"),
    ("Donatella", "Feel the Fire"),
    ("Leo Feat. Stine Moracchioli", "Zombie"),
    ("Modern Talking", "Brother Louie Mix 98 Extended Version"),
    ("SOX", "KA MA TA"),
    ("West Code", "Alone"),
    ("Captain Hollywood Project", "More and More Single Version"),
    ("Nikos Band", "GEORGIAN DISCO Live 23.11.23"),
    ("Abgefahren aber Okay", "Danza Kuduro"),
    ("Guru Josh", "Infinity"),
    ("Bomfunk MC's", "Freestyler"),
    ("Sadrican", "Dragostea Din Tei Cover"),
    ("Piter Mc", "Funky Cold Medina"),
    ("50 Cent", "In Da Club"),
    ("Bon Jovi", "It's My Life"),
    ("Slipknot", "Wait and Bleed"),
    ("FISHER", "Losing It"),
    ("Bon Jovi", "Livin' On A Prayer"),
    ("Snap!", "Rhythm Is a Dancer"),
    ("La Bouche", "Be My Lover"),
    # is patinkancios_muzikos_notepad.txt (kuriu dar nera grotuve)
    ("Eminem", "Without Me"),
    ("Nirvana", "Smells Like Teen Spirit"),
    ("Tream & Treamiboii", "Drago Augustino"),
]


def log(t: str) -> None:
    eil = time.strftime("%Y-%m-%d %H:%M:%S") + "  " + t
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(eil + "\n")
    print(eil, flush=True)


def saugus(v: str) -> str:
    v = unicodedata.normalize("NFKD", v)
    v = v.encode("ascii", "ignore").decode("ascii")
    v = re.sub(r'[<>:"/\\|?*]', "_", v)
    return re.sub(r"\s+", " ", v).strip()[:70]


def jau_yra(vardas: str) -> bool:
    for p in STAGE.glob("*.webm"):
        if p.stem.lower() == vardas.lower():
            return True
    return False


def main() -> int:
    log("=== PRADZIA: noru %d ===" % len(NORAI))
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       capture_output=True, text=True)
    log("yt-dlp: " + ((r.stdout or r.stderr or "").strip()[:80]))
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    log("ffmpeg: " + ((r.stdout or "NERA").splitlines()[0][:80] if r.stdout else "NERA"))

    ok, jau, fail = 0, 0, []
    for i, (artist, title) in enumerate(NORAI, 1):
        q = "%s %s" % (artist, title)
        vardas = saugus("%s - %s" % (artist, title))
        tikslas = STAGE / (vardas + ".webm")
        if tikslas.is_file() and tikslas.stat().st_size > 100_000:
            log("[%d/%d] JAU YRA: %s" % (i, len(NORAI), q))
            jau += 1
            continue
        log("[%d/%d] siunciu: %s" % (i, len(NORAI), q))
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
            "-f", "bestaudio[ext=webm]/bestaudio",
            "--output", str(STAGE / (vardas + ".%(ext)s")),
            "ytsearch1:" + q,
        ]
        try:
            rr = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            if rr.returncode == 0:
                # jei atsirado kitas plėtinys - pervardinu i .webm
                for p in STAGE.glob(vardas + ".*"):
                    if p.suffix.lower() != ".webm":
                        p.rename(STAGE / (vardas + ".webm"))
                f = STAGE / (vardas + ".webm")
                if f.is_file():
                    log("    OK: %s (%.1f MB)" % (q, f.stat().st_size / 1048576))
                    ok += 1
                else:
                    log("    FAIL (failo nera): %s" % q)
                    fail.append(q)
            else:
                log("    FAIL: %s :: %s" % (q, (rr.stderr or "")[-160:].replace("\n", " ")))
                fail.append(q)
        except Exception as e:
            log("    KLAIDA: %s :: %r" % (q, e))
            fail.append(q)

    log("=== BAIGTA: nauju %d, jau buvo %d, nepavyko %d ===" % (ok, jau, len(fail)))
    for q in fail:
        log("   NEPAVYKO: " + q)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())