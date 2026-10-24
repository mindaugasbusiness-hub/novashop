# -*- coding: utf-8 -*-
"""IVR testai (lokaliai, 127.0.0.1:8000)."""
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = "http://127.0.0.1:8000"
OK, FAIL = [], []


def post(path, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8")


def get(path):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()


def check(name, cond, extra=""):
    (OK if cond else FAIL).append(f"{name} {extra}".strip())
    print(("OK   " if cond else "FAIL ") + name + ((" | " + extra) if extra else ""))


def twiml_test(name, path, data, must=(), must_not=(), status_want=200):
    st, ct, text = post(path, data)
    try:
        root = ET.fromstring(text)
        valid = root.tag == "Response"
    except Exception as exc:
        check(name, False, f"XML klaida: {exc}")
        return ""
    hits = [m for m in must if m in text]
    bad = [m for m in must_not if m in text]
    ok = valid and st == status_want and "xml" in ct and len(hits) == len(must) and not bad
    check(name, ok, f"http={st} ct={ct} xml_valid={valid} found={len(hits)}/{len(must)} bad={bad}")
    if not ok:
        print("   >>>", text[:400])
    return text


print("=== 1. TwiML endpointai ===")
twiml_test("POST /twilio/voice", "/twilio/voice",
           {"CallSid": "TEST1", "From": "+37060000000", "To": "+16672395281"},
           must=['<Dial timeout="20"', "twilio/after-dial", 'callerId="+16672395281"',
                 "<Sip>sip:mvisminas2026@mindaugas-phone.sip.twilio.com</Sip>"])

twiml_test("POST /twilio/after-dial no-answer", "/twilio/after-dial",
           {"DialCallStatus": "no-answer", "CallSid": "TEST1"},
           must=["greet.mp3", "<Gather", 'numDigits="1"', "twilio/menu"])

twiml_test("POST /twilio/after-dial completed", "/twilio/after-dial",
           {"DialCallStatus": "completed", "CallSid": "TEST1"},
           must=["<Hangup/>"], must_not=["<Gather"])

twiml_test("POST /twilio/menu 1", "/twilio/menu", {"Digits": "1", "CallSid": "TEST1"},
           must=["prekes.mp3", "grizti9.mp3", "twilio/menu"])
twiml_test("POST /twilio/menu 2", "/twilio/menu", {"Digits": "2", "CallSid": "TEST1"},
           must=["klausimai.mp3", 'input="speech"', "twilio/speech"])
twiml_test("POST /twilio/menu 3", "/twilio/menu", {"Digits": "3", "CallSid": "TEST1"},
           must=["zinute.mp3", '<Record maxLength="120"', "twilio/recorded",
                 'playBeep="true"', 'trim="trim-silence"'])
twiml_test("POST /twilio/menu 0", "/twilio/menu", {"Digits": "0", "CallSid": "TEST1"},
           must=["perkelti.mp3", '<Dial callerId="+16672395281" timeout="30">+37063701637</Dial>'])
twiml_test("POST /twilio/menu 9", "/twilio/menu", {"Digits": "9", "CallSid": "TEST1"},
           must=["greet.mp3", "twilio/menu"])

print("=== 2. FAQ balsu ===")
twiml_test("POST /twilio/speech 'kaip registruotis'", "/twilio/speech",
           {"SpeechResult": "kaip registruotis", "CallSid": "TEST1"},
           must=["faq_4.mp3", "grizti9.mp3", "twilio/speech"])
twiml_test("POST /twilio/speech 'kiek laiko trunka lotas'", "/twilio/speech",
           {"SpeechResult": "kiek laiko trunka lotas", "CallSid": "TEST1"},
           must=["faq_11.mp3"])
twiml_test("POST /twilio/speech 'kas yra Vilkas'", "/twilio/speech",
           {"SpeechResult": "kas yra Vilkas", "CallSid": "TEST1"},
           must=["faq_14.mp3"])
twiml_test("POST /twilio/speech nesamone", "/twilio/speech",
           {"SpeechResult": "zodzodzod ble ble", "CallSid": "TEST1"},
           must=["nesupratau.mp3"])
twiml_test("POST /twilio/speech 3 (po atsakymo)", "/twilio/speech", {"Digits": "3", "CallSid": "TEST1"},
           must=["zinute.mp3", "<Record"])
twiml_test("POST /twilio/speech 9 (po atsakymo)", "/twilio/speech", {"Digits": "9", "CallSid": "TEST1"},
           must=["greet.mp3", "twilio/menu"])
twiml_test("POST /twilio/menu SpeechResult is karto", "/twilio/menu",
           {"SpeechResult": "ar siunciate i uzsieni", "CallSid": "TEST1"},
           must=["faq_18.mp3"])

print("=== 3. /voice failai ===")
st, ct, payload = get("/voice/greet.mp3")
check("GET /voice/greet.mp3", st == 200 and ct.startswith("audio/mpeg") and len(payload) > 5000,
      f"http={st} ct={ct} bytes={len(payload)}")
for name in ("prekes.mp3", "klausimai.mp3", "zinute.mp3", "aciu.mp3", "nesupratau.mp3", "iki.mp3",
             "perkelti.mp3", "grizti9.mp3"):
    st, ct, payload = get("/voice/" + name)
    check(f"GET /voice/{name}", st == 200 and len(payload) > 5000, f"http={st} bytes={len(payload)}")

st, ct, payload = get("/voice/../app.py")
check("kelio traversal blokuotas", st == 404, f"http={st}")
st, ct, payload = get("/voice/faq.json")
check("ne mp3 blokuotas", st == 404, f"http={st}")
st, ct, payload = get("/voice/nelyra.mp3")
check("nerastas failas 404", st == 404, f"http={st}")

print("=== 4. /twilio/log ===")
st, ct, payload = get("/twilio/log")
try:
    data = json.loads(payload.decode("utf-8"))
    pvz = json.dumps(data["ivykiai"][-1], ensure_ascii=False)[:150] if data.get("ivykiai") else ""
    check("GET /twilio/log", st == 200 and data.get("ok") and data.get("count", 0) > 0,
          f"http={st} count={data.get('count')} pvz={pvz}")
except Exception as exc:
    check("GET /twilio/log", False, str(exc))

print("=== 5. Svetaine ===")
st, ct, payload = get("/")
check("GET /", st == 200, f"http={st} bytes={len(payload)}")

print()
print(f"REZULTATAS: OK={len(OK)} FAIL={len(FAIL)}")
if FAIL:
    print("NEPAVYKO:")
    for f in FAIL:
        print(" -", f)

twiml_test("POST /twilio/menu tuscias", "/twilio/menu", {"Digits": "", "CallSid": "TEST1"},
           must=["nesupratau.mp3", "twilio/menu"])
twiml_test("POST /twilio/menu a=3 -> iki+Hangup", "/twilio/menu?a=3", {"Digits": "", "CallSid": "TEST1"},
           must=["nesupratau.mp3", "iki.mp3", "<Hangup/>"], must_not=["<Gather"])
