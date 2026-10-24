#!/usr/bin/env python3
# Tiksli UI pataisa /opt/aukcionas/app.py
# 1) .brand-top .radio-badge transform -6% -> -40%  (badge kairen)
# 2) .brand-name transform -14% -> -22% (kompensacija, kad tarpas badge-title liktu > 20px)
# 3) .pay-strip overflow:hidden -> visible (kad atsidarytu Taisykliu ir mokejimo paneles)
import re
import shutil
import sys

PATH = "/opt/aukcionas/app.py"
src = open(PATH, "r", encoding="utf-8", newline="").read()
orig = src

def rep(text, old, new, expect=1, label=""):
    n = text.count(old)
    if n != expect:
        print("STOP: '%s' radau %d karta (tikejausi %d) [%s]" % (old[:60], n, expect, label))
        sys.exit(2)
    print("OK  %-58s x%d" % (label, n))
    return text.replace(old, new)

# 1) badge kairen
src = rep(src, "transform:translate(-6%,23%);", "transform:translate(-40%,23%);", 1, "badge transform -6% -> -40%")

# 2) title kompensacija (3 vietos: 3754, 3777, 3782)
src = rep(src, "translateX(-14%)", "translateX(-22%)", 3, "brand-name -14% -> -22% (3 vietos)")

# 3) pay-strip overflow
new_src, n = re.subn(r"(\.pay-strip\{[^}]*?)overflow:hidden;", r"\1overflow:visible;", src, count=1, flags=re.S)
if n != 1:
    print("STOP: .pay-strip overflow pakeitimas nepavyko (n=%d)" % n)
    sys.exit(3)
src = new_src
print("OK  %-58s x1" % ".pay-strip overflow:hidden -> visible")

src = rep(src, ".pay-strip{top:10px;right:14px;left:auto;width:220px;max-width:220px;padding:6px 6px 7px;overflow:hidden;}",
          ".pay-strip{top:10px;right:14px;left:auto;width:220px;max-width:220px;padding:6px 6px 7px;overflow:visible;}",
          1, "media max-720 .pay-strip overflow -> visible")

if src == orig:
    print("STOP: niekas nepasikeite")
    sys.exit(4)

shutil.copyfile(PATH, "/tmp/app.py.pre_ui_patch")
open(PATH, "w", encoding="utf-8", newline="").write(src)
print("IRASYTA. Kopija pries irasyma: /tmp/app.py.pre_ui_patch")
print("Baitai: %d -> %d" % (len(orig), len(src)))
