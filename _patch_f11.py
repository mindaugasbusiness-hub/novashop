#!/usr/bin/env python3
# F11 pataisa: api_admin_vilkas_phone naudoja VISAS Vilko smegenu phone frazes per _vp
# (be n) ir VILKAS8_PHONE sarasa (12) rankiniam pasirinkimui (su n). CRLF islaikomas.
import os
import shutil
import sys
import time

PATH = "/opt/aukcionas/app.py"
BAK = "/opt/aukcionas/app.py.bak-f11-%s" % time.strftime("%Y-%m-%d")

OLD_LINES = [
    '@app.post("/api/admin/vilkas_phone")',
    "async def api_admin_vilkas_phone(request: Request):",
    '    """F11: Mindaugas paleidžia vieną iš 3 klasikinių telefono atsiliepimų (ciklas 1→2→3→1)."""',
    "    body = await request.json()",
    '    if body.get("password") != ADMIN_PASSWORD:',
    '        raise HTTPException(403, "neteisingas slaptazodis")',
    "    core = list(VILKAS8_PHONE_CORE)",
    "    if not core:",
    '        raise HTTPException(500, "nera telefono fraziu")',
    '    raw_n = body.get("n")',
    '    if raw_n is None or raw_n == "" or str(raw_n).lower() == "next":',
    '        idx = int(_phone_manual_n.get("n") or 0) % len(core)',
    '        _phone_manual_n["n"] = (idx + 1) % len(core)',
    "    else:",
    "        try:",
    "            idx = max(0, min(len(core) - 1, int(raw_n) - 1))",
    "        except Exception:",
    "            idx = 0",
    '        _phone_manual_n["n"] = (idx + 1) % len(core)',
    "    text = core[idx]",
    "    n = idx + 1",
    "    lot_id = None",
    "    try:",
    "        con = db()",
    "        try:",
    "            lot = get_live_lot(con) or get_active_lot(con)",
    "            if lot:",
    '                lot_id = lot["id"]',
    "        finally:",
    "            con.close()",
    "    except Exception:",
    "        pass",
    '    uk = f"phone_manual:{time.time_ns()}:{n}"',
    "    emit_event(",
    '        "phone",',
    '        {"lot_id": lot_id, "n": n, "text": text, "phrase_id": None, "manual": True},',
    "        95,",
    "        45,",
    "        uk,",
    "    )",
    "    return {",
    '        "ok": True,',
    '        "n": n,',
    '        "text": text,',
    '        "next_n": int(_phone_manual_n.get("n") or 0) + 1,',
    '        "core_count": len(core),',
    "    }",
]

NEW_LINES = [
    '@app.post("/api/admin/vilkas_phone")',
    "async def api_admin_vilkas_phone(request: Request):",
    '    """F11: Mindaugas paleidžia telefono atsiliepimą.',
    '    Be `n` (arba n="next") — frazę renka Vilko smegenys per _vp (visa rotacija, 30 fraziu).',
    '    Su `n` — rankinis pasirinkimas is VILKAS8_PHONE saraso (12 fraziu)."""',
    "    body = await request.json()",
    '    if body.get("password") != ADMIN_PASSWORD:',
    '        raise HTTPException(403, "neteisingas slaptazodis")',
    "    phrases = list(VILKAS8_PHONE) or list(VILKAS8_PHONE_CORE)",
    "    if not phrases:",
    '        raise HTTPException(500, "nera telefono fraziu")',
    '    raw_n = body.get("n")',
    "    phrase_id = None",
    '    source = "list"',
    "    n = 0",
    '    if raw_n is None or raw_n == "" or str(raw_n).lower() == "next":',
    "        # Smegenu frazes: _vp renka is visu phone fraziu (be 2-is-eiles pasikartojimu)",
    '        part = _vp("phone", time.time_ns(), phrases)',
    '        text = str(part.get("text") or phrases[0])',
    '        phrase_id = part.get("phrase_id")',
    '        source = "brain"',
    "        try:",
    "            n = phrases.index(text) + 1",
    "        except ValueError:",
    "            n = 0",
    "    else:",
    "        try:",
    "            idx = max(0, min(len(phrases) - 1, int(raw_n) - 1))",
    "        except Exception:",
    "            idx = 0",
    "        text = phrases[idx]",
    "        n = idx + 1",
    '    _phone_manual_n["n"] = (n % len(phrases)) if n > 0 else 0',
    "    lot_id = None",
    "    try:",
    "        con = db()",
    "        try:",
    "            lot = get_live_lot(con) or get_active_lot(con)",
    "            if lot:",
    '                lot_id = lot["id"]',
    "        finally:",
    "            con.close()",
    "    except Exception:",
    "        pass",
    '    uk = f"phone_manual:{time.time_ns()}:{n}"',
    "    emit_event(",
    '        "phone",',
    '        {"lot_id": lot_id, "n": n, "text": text, "phrase_id": phrase_id, "manual": True},',
    "        95,",
    "        45,",
    "        uk,",
    "    )",
    "    return {",
    '        "ok": True,',
    '        "n": n,',
    '        "text": text,',
    '        "next_n": int(_phone_manual_n.get("n") or 0) + 1,',
    '        "core_count": len(phrases),',
    '        "source": source,',
    '        "phrase_id": phrase_id,',
    "    }",
]

OLD = "\r\n".join(OLD_LINES)
NEW = "\r\n".join(NEW_LINES)

with open(PATH, "r", encoding="utf-8", newline="") as f:
    src = f.read()

cnt = src.count(OLD)
print("OLD rastas kartu:", cnt)
if cnt != 1:
    print("STOP: anchor nerastas arba ne unikalus")
    sys.exit(3)

if not os.path.exists(BAK):
    shutil.copy2(PATH, BAK)
    print("BACKUP:", BAK)
else:
    print("BACKUP jau yra:", BAK)

out = src.replace(OLD, NEW, 1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(out)

# patikra
with open(PATH, "r", encoding="utf-8", newline="") as f:
    chk = f.read()
print("VILKAS8_PHONE sarasas panaudotas:", chk.count("phrases = list(VILKAS8_PHONE)"))
print("VILKAS8_PHONE_CORE fallback:", chk.count("or list(VILKAS8_PHONE_CORE)"))
print("source= brain:", chk.count('source = "brain"'))
print("PATCHED OK")
