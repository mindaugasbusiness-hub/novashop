#!/usr/bin/env python3
# Tikslas: patraukti .brand-evening ("VAKARE 20:00") kairen, kad centras butu po .brand-name centru.
# Ismatuota (1280px, live): brand-name centras 454.8; .brand-evening naturalus centras 626.4; plotis 166.1 (1% = 1.661px)
# Reikia poslinkio -171.6px -> -103.3% -> naudojam -103%.
# Keiciama TIK X dalis: translate(-32%,-23%) -> translate(-103%,-23%), 3 vietos (3771, 3779, 3783).
import shutil
import sys

PATH = "/opt/aukcionas/app.py"
src = open(PATH, "r", encoding="utf-8", newline="").read()
orig = src

OLD = "translate(-32%,-23%)"
NEW = "translate(-103%,-23%)"

n = src.count(OLD)
if n != 3:
    print("STOP: '%s' radau %d karta (tikejausi 3)" % (OLD, n))
    sys.exit(2)

src = src.replace(OLD, NEW)
print("OK  %s -> %s  x%d" % (OLD, NEW, n))

if src == orig:
    print("STOP: niekas nepasikeite")
    sys.exit(4)

shutil.copyfile(PATH, "/tmp/app.py.pre_evening_patch")
open(PATH, "w", encoding="utf-8", newline="").write(src)
print("IRASYTA. Kopija pries irasyma: /tmp/app.py.pre_evening_patch")
print("Baitai: %d -> %d" % (len(orig), len(src)))
