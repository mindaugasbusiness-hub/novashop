# -*- coding: utf-8 -*-
"""Ideda 2 eilutes i /opt/aukcionas/app.py po app.mount('/photos', ...) - IVR routeris."""
from pathlib import Path
import sys

TARGET = Path("/opt/aukcionas/app.py")
MARKER = 'app.mount("/photos"'
IMPORT_LINE = "from ivr import router as ivr_router"
INCLUDE_LINE = "app.include_router(ivr_router)"

raw = TARGET.read_bytes().decode("utf-8")
if IMPORT_LINE in raw and INCLUDE_LINE in raw:
    print("JAU_IDETA - nieko nekeiciu")
    sys.exit(0)

lines = raw.splitlines(keepends=True)
idx = None
for i, line in enumerate(lines):
    if MARKER in line:
        idx = i
        break
if idx is None:
    print("NERASTA app.mount('/photos') eilutes")
    sys.exit(1)

eol = "\r\n" if lines[idx].endswith("\r\n") else "\n"
new = [IMPORT_LINE + eol, INCLUDE_LINE + eol]
lines[idx + 1:idx + 1] = new
TARGET.write_bytes("".join(lines).encode("utf-8"))
print(f"IDETA po {idx + 1} eilutes (eol={eol!r})")
