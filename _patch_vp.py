#!/usr/bin/env python3
# Pataisa VPS /opt/aukcionas/app.py: funkcija _vp() — frazes nebesikartos.
# 1) pridedama modulio lygio atmintis _VP_RECENT / _VP_LAST (+ from collections import deque)
# 2) _vp parenka fraze: 0.55*kokybe + 0.35*atsitiktinumas + 0.10*naujumas,
#    ismeta paskutines 8 naudotas ir paskutine (kad nebutu dvieju is eiles vienodu),
#    sekla su time.time_ns() (kiekvienas kvietimas skirtingas).
# NIEKO kito nelieciama. Pries keitima daromas backup (cp -n).
import ast
import datetime
import sys
import time

import paramiko

env = {}
with open("/workspace/.aukc_env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

HOST = env.get("AUKC_HOST", "5.175.171.113")
USER = env.get("AUKC_USER", "root")
PW = env.get("AUKC_PW")
PORT = int(env.get("AUKC_PORT", "22"))
if not PW:
    print("NERA AUKC_PW", file=sys.stderr)
    sys.exit(2)

REMOTE = "/opt/aukcionas/app.py"
LOCAL_BEFORE = "/workspace/_app_before_vp.py"
LOCAL_AFTER = "/workspace/_app_after_vp.py"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M")
BAK = REMOTE + ".bak-vp-" + STAMP

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30,
            allow_agent=False, look_for_keys=False, banner_timeout=30, auth_timeout=30)


def sh(cmd, t=300):
    _i, out, err = cli.exec_command(cmd, timeout=t)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return out.channel.recv_exit_status(), o, e


rc, o, e = sh("cp -n %s %s; ls -la %s" % (REMOTE, BAK, BAK))
print("[1] BACKUP rc=%s %s" % (rc, (o.strip() or e.strip())))

sftp = cli.open_sftp()
sftp.get(REMOTE, LOCAL_BEFORE)
sftp.close()
content = open(LOCAL_BEFORE, "rb").read().decode("utf-8")
print("[2] Nuskaityta %d baitu, eiluciu %d" % (len(content.encode("utf-8")), content.count("\n") + 1))

CRLF = "\r\n"


OLD_IMPORT = "import random as _vk_random" + CRLF
NEW_IMPORT = "import random as _vk_random" + CRLF + "from collections import deque" + CRLF

OLD_FUNC = (
    'def _vp(kind, seed, fallback_list):' + CRLF +
    '    """Thompson sampling i\u0161 smegen\u0173. Gr\u0105\u017eina payload dal\u012f {"text","phrase_id"}."""' + CRLF +
    '    try:' + CRLF +
    '        arr = [p for p in (vilko_brain().get("frazes") or {}).get(kind, []) if p.get("aktyvi", True) and p.get("tekstas")]' + CRLF +
    '    except Exception:' + CRLF +
    '        arr = []' + CRLF +
    '    if not arr:' + CRLF +
    '        fl = list(fallback_list or [""])' + CRLF +
    '        return {"text": fl[int(seed) % len(fl)], "phrase_id": None}' + CRLF +
    '    rnd = _vk_random.Random(f"{kind}:{seed}:{int(time.time() // 900)}")' + CRLF +
    '    best, bv = None, -1.0' + CRLF +
    '    for p in arr:' + CRLF +
    '        v = rnd.betavariate(max(0.01, float(p.get("a", 1))), max(0.01, float(p.get("b", 1))))' + CRLF +
    '        if v > bv:' + CRLF +
    '            best, bv = p, v' + CRLF +
    '    return {"text": best["tekstas"], "phrase_id": best["id"]}' + CRLF
)

NEW_FUNC = CRLF.join([
    '_VP_RECENT = {}  # kind -> deque(maxlen=8) paskutiniu pasirinktu fraziu id (kad nesikartotu)',
    '_VP_LAST = {}    # kind -> paskutinis pasirinktas fraziu id (kad nebutu dvieju is eiles vienodu)',
    '',
    '',
    'def _vp(kind, seed, fallback_list):',
    '    """Frazes parinkimas: 0.55*kokybe(a/(a+b)) + 0.35*atsitiktinumas + 0.10*naujumas.',
    '    To paties kind frazes nesikartoja: paskutines 8 laikomos atmintyje,',
    '    dvieju is eiles vienodu nebus. Grazina payload dali {"text","phrase_id"}."""',
    '    try:',
    '        arr = [p for p in (vilko_brain().get("frazes") or {}).get(kind, []) if p.get("aktyvi", True) and p.get("tekstas")]',
    '    except Exception:',
    '        arr = []',
    '    if not arr:',
    '        fl = list(fallback_list or [""])',
    '        return {"text": fl[int(seed) % len(fl)], "phrase_id": None}',
    '    recent = _VP_RECENT.setdefault(kind, deque(maxlen=8))',
    '    pool = [p for p in arr if str(p.get("id")) not in recent]',
    '    if not pool:',
    '        pool = list(arr)',
    '    last = _VP_LAST.get(kind)',
    '    if len(pool) > 1 and last is not None:',
    '        pool = [p for p in pool if str(p.get("id")) != str(last)] or pool',
    '    rnd = _vk_random.Random(f"{kind}:{seed}:{time.time_ns()}")',
    '    best, bv = None, -1.0',
    '    for p in pool:',
    '        a = max(0.01, float(p.get("a", 1)))',
    '        b = max(0.01, float(p.get("b", 1)))',
    '        try:',
    '            kartai = float(p.get("kartai") or 0)',
    '        except Exception:',
    '            kartai = 0.0',
    '        score = 0.55 * (a / (a + b)) + 0.35 * rnd.random() + 0.10 * (1.0 / (1.0 + kartai / 30.0))',
    '        if score > bv:',
    '            best, bv = p, score',
    '    chosen = str(best.get("id"))',
    '    recent.append(chosen)',
    '    _VP_LAST[kind] = chosen',
    '    return {"text": best["tekstas"], "phrase_id": best.get("id")}',
]) + CRLF

for name, old in (("import", OLD_IMPORT), ("_vp", OLD_FUNC)):
    cnt = content.count(old)
    print("[3] atitikmenys %s: %d" % (name, cnt))
    if cnt != 1:
        sys.exit("STOP: %s atitikmenys=%d (turi buti 1)" % (name, cnt))

new_content = content.replace(OLD_IMPORT, NEW_IMPORT).replace(OLD_FUNC, NEW_FUNC)
ast.parse(new_content)
print("[4] Sintakses patikra (lokaliai) OK; naujas dydis %d baitu" % len(new_content.encode("utf-8")))

with open(LOCAL_AFTER, "w", encoding="utf-8", newline="") as fh:
    fh.write(new_content)

sftp = cli.open_sftp()
sftp.put(LOCAL_AFTER, REMOTE)
sftp.close()
print("[5] Ikelta i %s" % REMOTE)

rc, o, e = sh("/opt/aukcionas/.venv/bin/python -c \"import ast;ast.parse(open('%s',encoding='utf-8').read());print('SYNTAX OK')\"" % REMOTE)
print("[6] Sintakses patikra serveryje rc=%s %s %s" % (rc, o.strip(), e.strip()))

rc, o, e = sh("grep -n 'from collections import deque\\|_VP_RECENT = \\|_VP_LAST = \\|def _vp(' %s" % REMOTE)
print("[7] Eilutes po pakeitimo:\n%s" % o.strip())

rc, o, e = sh("systemctl restart aukcionas.service")
print("[8] restart rc=%s %s" % (rc, (o or e).strip()))
time.sleep(30)

rc, o, e = sh("systemctl is-active aukcionas.service")
print("[9] is-active: %s" % o.strip())
rc, o, e = sh("curl -s -o /dev/null -w '%%{http_code}' http://127.0.0.1:8000/")
print("[10] HTTP / : %s" % o.strip())
rc, o, e = sh("curl -s -X POST http://127.0.0.1:8000/twilio/voice -d 'CallSid=T1' | head -c 300")
print("[11] IVR /twilio/voice rc=%s:\n%s" % (rc, o.strip()))
rc, o, e = sh("/opt/aukcionas/.venv/bin/python -c \"import json;d=json.load(open('/opt/aukcionas/vilko_mokykla/smegenys.json'));print('phone aktyvios:',len([x for x in d['frazes'].get('phone',[]) if x.get('aktyvi',True)]));print('phone_catchup aktyvios:',len([x for x in d['frazes'].get('phone_catchup',[]) if x.get('aktyvi',True)]))\"")
print("[12] Frazes: %s %s" % (o.strip(), e.strip()))
rc, o, e = sh("grep -n 'phone_catchup' %s | head -10" % REMOTE)
print("[13] phone_catchup paminejimai app.py:\n%s" % (o.strip() or "(nera)"))

cli.close()
print("DONE backup=%s" % BAK)
