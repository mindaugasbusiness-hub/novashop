# -*- coding: utf-8 -*-
"""IVR (balso meniu) penktadienio aukcionui - Vilkas atsiliepia i skambucius.

Eiga:
  1. Skambutis i Twilio numeri -> POST /twilio/voice -> Dial i Linphone (SIP) 20 s.
  2. Jei nepakelta -> POST /twilio/after-dial -> Vilkas pristato meniu.
  3. Meniu: 1 - prekiu priemimas, 2 - klausimai balsu (FAQ), 3 - zinute,
     0 - perkelti vedejui, 9 - grizti i meniu.

Failai:
  /opt/aukcionas/voice/*.mp3       - promptai (edge-tts)
  /opt/aukcionas/voice/faq.json    - FAQ raktazodziai + atsakymai
  /opt/aukcionas/voice/faq_<nr>.mp3- FAQ atsakymu cache (lazy)
  /opt/aukcionas/voicebox/*.mp3    - irasytos zinutes
  /opt/aukcionas/voicebox/ivr.log  - ivykiu zurnalas (JSON eilutes)
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import threading
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

try:  # .env papildymas, jei modulis paleistas ne per systemd
    from dotenv import load_dotenv

    load_dotenv("/opt/aukcionas/.env")
except Exception:  # pragma: no cover
    pass

BASE_DIR = Path(os.environ.get("AUKCIONAS_DATA_DIR") or "/opt/aukcionas")
VOICE_DIR = BASE_DIR / "voice"
VOICEBOX_DIR = BASE_DIR / "voicebox"
FAQ_PATH = VOICE_DIR / "faq.json"
IVR_LOG = VOICEBOX_DIR / "ivr.log"

PUBLIC_BASE = (os.environ.get("IVR_PUBLIC_BASE") or "https://penktadienioaukcionas.lt").rstrip("/")
TWILIO_NUMBER = (os.environ.get("TWILIO_PHONE_NUMBER") or "+16672395281").strip()
OWNER_NUMBER = (os.environ.get("MY_PHONE_NUMBER") or "+37063701637").strip()
SIP_USER = (os.environ.get("IVR_SIP_USER") or "mvisminas2026").strip()
SIP_DOMAIN = (os.environ.get("IVR_SIP_DOMAIN") or "mindaugas-phone.sip.twilio.com").strip()
SIP_URI = f"sip:{SIP_USER}@{SIP_DOMAIN}"
NTFY_TOPIC = (os.environ.get("IVR_NTFY_TOPIC") or "cline-alertai-7f3a91b2c5d84e60").strip()
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

EDGE_BIN = (os.environ.get("IVR_EDGE_TTS") or str(BASE_DIR / ".venv" / "bin" / "edge-tts")).strip()
EDGE_VOICE = (os.environ.get("IVR_EDGE_VOICE") or "lt-LT-LeonasNeural").strip()
EDGE_RATE = (os.environ.get("IVR_EDGE_RATE") or "-5%").strip()
EDGE_PITCH = (os.environ.get("IVR_EDGE_PITCH") or "-2Hz").strip()

DIAL_TIMEOUT = int(os.environ.get("IVR_DIAL_TIMEOUT") or 20)
MAX_LOOPS = int(os.environ.get("IVR_MAX_LOOPS") or 3)
GATHER_TIMEOUT = int(os.environ.get("IVR_GATHER_TIMEOUT") or 8)
SPEECH_TIMEOUT = (os.environ.get("IVR_SPEECH_TIMEOUT") or "auto").strip()
LANG = "lt-LT"

router = APIRouter()

_events: deque = deque(maxlen=200)
_log_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Pagalbines funkcijos
# --------------------------------------------------------------------------- #
def esc(value) -> str:
    """XML escape (& -> &amp; ir t.t.)."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def twiml(inner: str) -> Response:
    """Sukompiliuoja TwiML atsakyma."""
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response>' + inner + "</Response>"
    return Response(content=xml, media_type="application/xml")


def play(name: str) -> str:
    return f"<Play>{esc(PUBLIC_BASE + '/voice/' + name)}</Play>"


def gather(
    action: str,
    *,
    num_digits=None,
    timeout=None,
    input_type="dtmf speech",
    speech_timeout=None,
    inner: str = "",
) -> str:
    attrs = [
        f'action="{esc(action)}"',
        'method="POST"',
        f'timeout="{int(timeout if timeout is not None else GATHER_TIMEOUT)}"',
        f'input="{esc(input_type)}"',
        f'language="{esc(LANG)}"',
        f'speechTimeout="{esc(speech_timeout or SPEECH_TIMEOUT)}"',
    ]
    if num_digits:
        attrs.append(f'numDigits="{int(num_digits)}"')
    return f'<Gather {" ".join(attrs)}>{inner}</Gather>'


def menu_action(loop: int) -> str:
    return f"{PUBLIC_BASE}/twilio/menu?a={max(0, int(loop))}"


def speech_action(loop: int) -> str:
    return f"{PUBLIC_BASE}/twilio/speech?a={max(0, int(loop))}"


def loop_of(request: Request, form=None) -> int:
    raw = None
    try:
        raw = request.query_params.get("a")
    except Exception:
        raw = None
    if raw is None and form is not None:
        raw = form.get("a")
    try:
        return max(0, min(20, int(str(raw).strip())))
    except Exception:
        return 0


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log_event(kind: str, **fields) -> dict:
    """Iraso ivyki i atminti ir /opt/aukcionas/voicebox/ivr.log (JSON eilute)."""
    rec = {"laikas": now_utc(), "ivykis": kind}
    for key, value in fields.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            rec[key] = text[:300]
    with _log_lock:
        _events.append(rec)
        try:
            VOICEBOX_DIR.mkdir(parents=True, exist_ok=True)
            with open(IVR_LOG, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return rec


# --------------------------------------------------------------------------- #
# FAQ (raktazodziu sistema, be LLM)
# --------------------------------------------------------------------------- #
_faq_lock = threading.Lock()
_faq_cache: dict = {"mtime": 0.0, "data": []}


def load_faq() -> list:
    try:
        mtime = FAQ_PATH.stat().st_mtime
    except OSError:
        return []
    with _faq_lock:
        if _faq_cache["mtime"] != mtime:
            try:
                raw = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
                entries = raw.get("irasa") if isinstance(raw, dict) else raw
                _faq_cache["data"] = [e for e in (entries or []) if isinstance(e, dict)]
                _faq_cache["mtime"] = mtime
            except Exception as exc:
                log_event("faq_klaida", klaida=type(exc).__name__)
                return list(_faq_cache["data"])
        return list(_faq_cache["data"])


def normalize(text: str) -> str:
    """Mazosios raides, be diakritiku, tik raides/skaiciai ir tarpai."""
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def faq_match(speech: str):
    """Grazina (irasas, balu_suma) arba (None, 0.0)."""
    query = normalize(speech)
    if not query:
        return None, 0.0
    best, best_score = None, 0.0
    for entry in load_faq():
        score = 0.0
        for key in entry.get("raktai") or []:
            keyword = normalize(key)
            if keyword and keyword in query:
                score += 1.0 + len(keyword) / 12.0
        if score > best_score:
            best, best_score = entry, score
    return best, best_score


async def ensure_faq_audio(nr, text: str):
    """Lazy: sugeneruoja faq_<nr>.mp3 su edge-tts, jei jo dar nera."""
    if not text:
        return None
    try:
        path = VOICE_DIR / f"faq_{int(nr)}.mp3"
    except Exception:
        return None
    if path.is_file() and path.stat().st_size > 1000:
        return path.name
    try:
        VOICE_DIR.mkdir(parents=True, exist_ok=True)
        process = await asyncio.create_subprocess_exec(
            EDGE_BIN,
            "--voice", EDGE_VOICE,
            f"--rate={EDGE_RATE}",
            f"--pitch={EDGE_PITCH}",
            "--text", text,
            "--write-media", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await asyncio.wait_for(process.communicate(), timeout=30)
    except Exception as exc:
        log_event("faq_tts_klaida", nr=nr, klaida=type(exc).__name__)
        return None
    if path.is_file() and path.stat().st_size > 1000:
        log_event("faq_tts", nr=nr, failas=path.name, dydis=path.stat().st_size)
        return path.name
    detail = (err or b"").decode("utf-8", "replace").strip().splitlines()
    log_event(
        "faq_tts_tuscias",
        nr=nr,
        kodas=process.returncode,
        klaida=(detail[-1][:200] if detail else ""),
    )
    return None



# --------------------------------------------------------------------------- #
# Twilio kredencialai ir pranesimai
# --------------------------------------------------------------------------- #
def twilio_credentials():
    """(account_sid, auth_token) is aplinkos arba /root/.twilio* - reiksmiu nespausdinam."""
    sid = (os.environ.get("TWILIO_ACCOUNT_SID") or os.environ.get("TWILIO_SID") or "").strip()
    token = (os.environ.get("TWILIO_AUTH_TOKEN") or os.environ.get("TWILIO_TOKEN") or "").strip()
    if sid and token:
        return sid, token
    candidates = [Path("/root/.twilio"), Path("/root/.twilio.json"), Path("/root/twilio.env")]
    for candidate in candidates:
        try:
            if not candidate.is_file():
                continue
            raw = candidate.read_text(encoding="utf-8", errors="replace").strip()
            if raw.startswith("{"):
                data = json.loads(raw)
                sid = sid or str(data.get("account_sid") or data.get("sid") or "").strip()
                token = token or str(data.get("auth_token") or data.get("token") or "").strip()
            else:
                for line in raw.splitlines():
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip().upper()
                    if key in ("TWILIO_ACCOUNT_SID", "ACCOUNT_SID", "SID"):
                        sid = sid or value.strip()
                    elif key in ("TWILIO_AUTH_TOKEN", "AUTH_TOKEN", "TOKEN"):
                        token = token or value.strip()
            if sid and token:
                return sid, token
        except Exception:
            continue
    return sid, token


def basic_auth_header(sid: str, token: str) -> str:
    raw = f"{sid}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def save_recording(recording_url: str, call_sid: str) -> str:
    """Parsisiuncia irasa is Twilio i /opt/aukcionas/voicebox/<data>_<CallSid>.mp3."""
    url = (recording_url or "").strip()
    if not url:
        return ""
    if not url.lower().endswith(".mp3"):
        url = url + ".mp3"
    safe_sid = re.sub(r"[^A-Za-z0-9_-]", "_", call_sid or "unknown") or "unknown"
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = VOICEBOX_DIR / f"{stamp}_{safe_sid}.mp3"
    request = urllib.request.Request(url)
    sid, token = twilio_credentials()
    if sid and token:
        request.add_header("Authorization", basic_auth_header(sid, token))
    try:
        VOICEBOX_DIR.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read()
        if not payload:
            log_event("irasas_tuscias", CallSid=call_sid)
            return ""
        dest.write_bytes(payload)
        log_event("irasas_issaugotas", CallSid=call_sid, failas=str(dest), dydis=len(payload))
        return str(dest)
    except urllib.error.HTTPError as exc:
        log_event("irasas_klaida", CallSid=call_sid, kodas=exc.code)
    except Exception as exc:
        log_event("irasas_klaida", CallSid=call_sid, klaida=type(exc).__name__)
    return ""


def notify_ntfy(message: str, path: str = "") -> None:
    try:
        request = urllib.request.Request(NTFY_URL, data=message.encode("utf-8"), method="POST")
        request.add_header("Title", "Nauja zinute telefone")
        request.add_header("Tags", "telephone")
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
        log_event("ntfy_ok", failas=path)
    except Exception as exc:
        log_event("ntfy_klaida", klaida=type(exc).__name__)


def notify_sms(body: str) -> None:
    sid, token = twilio_credentials()
    if not (sid and token):
        log_event("sms_praleista", priezastis="nera_twilio_raktu")
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    payload = urllib.parse.urlencode(
        {"To": OWNER_NUMBER, "From": TWILIO_NUMBER, "Body": body}
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Authorization", basic_auth_header(sid, token))
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
        log_event("sms_ok", kam=OWNER_NUMBER)
    except urllib.error.HTTPError as exc:
        log_event("sms_klaida", kodas=exc.code)
    except Exception as exc:
        log_event("sms_klaida", klaida=type(exc).__name__)


def notify_new_message(from_number: str, duration: str, path: str) -> None:
    notify_ntfy(f"Nuo {from_number}, trukme {duration}s, failas {path}", path)
    notify_sms(f"Aukciono telefone nauja zinute nuo {from_number} ({duration}s)")


# --------------------------------------------------------------------------- #
# TwiML atsakymai
# --------------------------------------------------------------------------- #
def response_menu_loop(loop: int) -> Response:
    """Greeting + meniu (1/2/3/0/9)."""
    return twiml(play("greet.mp3") + gather(menu_action(loop), num_digits=1))


def response_prekes(loop: int) -> Response:
    """Prekiu priemimas + vel 1/2/3 pasirinkimas."""
    inner = play("prekes.mp3") + play("grizti9.mp3") + gather(menu_action(loop), num_digits=1)
    return twiml(inner)


def response_klausimai(loop: int) -> Response:
    """Balso klausimas -> FAQ (atsakymas sugeneruojamas atskirai)."""
    inner = play("klausimai.mp3") + gather(speech_action(loop), input_type="speech")
    return twiml(inner)


def response_record() -> Response:
    """Zinutes irasymas (iki 120 s)."""
    record = (
        f'<Record maxLength="120" action="{esc(PUBLIC_BASE + "/twilio/recorded")}" '
        'method="POST" playBeep="true" trim="trim-silence"/>'
    )
    return twiml(play("zinute.mp3") + record)


def response_transfer() -> Response:
    """Perkelimas vedejui."""
    dial = f'<Dial callerId="{esc(TWILIO_NUMBER)}" timeout="30">{esc(OWNER_NUMBER)}</Dial>'
    return twiml(play("perkelti.mp3") + dial)


def response_fallback(loop: int) -> Response:
    """Nesuprato arba nieko neivede - prasom pakartoti; po MAX_LOOPS - atsisveikinam."""
    if loop >= MAX_LOOPS:
        return twiml(play("nesupratau.mp3") + play("iki.mp3") + "<Hangup/>")
    return twiml(play("nesupratau.mp3") + gather(menu_action(loop + 1), num_digits=1))


def handle_digits(digits: str, loop: int):
    """DTMF pasirinkimas -> atsakymas arba None, jei skaicius neatpazintas."""
    code = (digits or "").strip()
    if code == "1":
        return response_prekes(loop + 1)
    if code == "2":
        return response_klausimai(loop + 1)
    if code == "3":
        return response_record()
    if code == "0":
        return response_transfer()
    if code == "9":
        return response_menu_loop(loop + 1)
    return None


async def answer_speech(speech: str, loop: int, call_sid: str, from_number: str) -> Response:
    """FAQ atsakymas i balsu pasakyta klausima."""
    entry, score = faq_match(speech)
    if entry is None:
        log_event("faq_nerastas", CallSid=call_sid, From=from_number, tekstas=speech, loop=loop)
        return response_fallback(loop)
    nr = entry.get("nr")
    answer = (entry.get("atsakymas") or "").strip()
    log_event(
        "faq_atsakymas",
        CallSid=call_sid,
        From=from_number,
        nr=nr,
        tekstas=speech,
        balas=round(score, 2),
    )
    name = await ensure_faq_audio(nr, answer)
    if not name:
        return response_fallback(loop)
    inner = play(name) + play("grizti9.mp3") + gather(speech_action(loop + 1), num_digits=1)
    return twiml(inner)


# --------------------------------------------------------------------------- #
# Endpointai
# --------------------------------------------------------------------------- #
@router.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Skambutis i Twilio numeri - pirmiausia bandome Vilką (Linphone per SIP)."""
    form = await request.form()
    log_event("skambutis", CallSid=form.get("CallSid"), From=form.get("From"), To=form.get("To"))
    dial = (
        f'<Dial timeout="{DIAL_TIMEOUT}" '
        f'action="{esc(PUBLIC_BASE + "/twilio/after-dial")}" '
        f'method="POST" callerId="{esc(TWILIO_NUMBER)}">'
        f"<Sip>{esc(SIP_URI)}</Sip></Dial>"
    )
    return twiml(dial)


@router.post("/twilio/after-dial")
async def twilio_after_dial(request: Request):
    """Vilkas pakėlė - baigiam. Nepakėlė - pristatome meniu."""
    form = await request.form()
    status = (form.get("DialCallStatus") or "").strip().lower()
    log_event(
        "po_skambucio",
        CallSid=form.get("CallSid"),
        From=form.get("From"),
        DialCallStatus=status or "none",
    )
    if status in ("completed", "answered"):
        return twiml("<Hangup/>")
    return response_menu_loop(1)


@router.get("/voice/{failas}")
async def voice_file(failas: str):
    """MP3 promptu atidavimas. Leidziami tik [A-Za-z0-9_.-]+ ir .mp3."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", failas or "") or not failas.lower().endswith(".mp3"):
        raise HTTPException(status_code=404, detail="not found")
    if ".." in failas:
        raise HTTPException(status_code=404, detail="not found")
    path = (VOICE_DIR / failas).resolve()
    try:
        path.relative_to(VOICE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type="audio/mpeg")



@router.post("/twilio/menu")
async def twilio_menu(request: Request):
    """Pagrindinis meniu: DTMF arba balsas."""
    form = await request.form()
    digits = (form.get("Digits") or "").strip()
    speech = (form.get("SpeechResult") or "").strip()
    call_sid = form.get("CallSid")
    from_number = form.get("From")
    loop = loop_of(request, form)
    log_event(
        "meniu",
        CallSid=call_sid,
        From=from_number,
        digits=digits,
        tekstas=speech,
        loop=loop,
    )
    if digits:
        answer = handle_digits(digits, loop)
        if answer is not None:
            return answer
    if speech:
        return await answer_speech(speech, loop, call_sid, from_number)
    return response_fallback(loop)


@router.post("/twilio/speech")
async def twilio_speech(request: Request):
    """Balso klausimas po 2 pasirinkimo (arba testi pokalbi po atsakymo)."""
    form = await request.form()
    digits = (form.get("Digits") or "").strip()
    speech = (form.get("SpeechResult") or "").strip()
    call_sid = form.get("CallSid")
    from_number = form.get("From")
    loop = loop_of(request, form)
    log_event(
        "kalba",
        CallSid=call_sid,
        From=from_number,
        digits=digits,
        tekstas=speech,
        loop=loop,
    )
    if digits:
        answer = handle_digits(digits, loop)
        if answer is not None:
            return answer
    if not speech:
        return response_fallback(loop)
    return await answer_speech(speech, loop, call_sid, from_number)


@router.post("/twilio/recorded")
async def twilio_recorded(request: Request):
    """Irasyta zinute: parsisiunciam, pranesam (ntfy + SMS) ir atsakom padėka."""
    form = await request.form()
    call_sid = (form.get("CallSid") or "unknown").strip()
    from_number = (form.get("From") or "unknown").strip()
    duration = (form.get("RecordingDuration") or "0").strip()
    recording_url = (form.get("RecordingUrl") or "").strip()
    log_event(
        "zinute",
        CallSid=call_sid,
        From=from_number,
        trukme=duration,
        irasas=recording_url,
    )
    saved = ""
    if recording_url:
        saved = await asyncio.to_thread(save_recording, recording_url, call_sid)
    threading.Thread(
        target=notify_new_message,
        args=(from_number, duration, saved or recording_url),
        daemon=True,
    ).start()
    return twiml(play("aciu.mp3") + "<Hangup/>")


@router.get("/twilio/log")
async def twilio_log():
    """Paskutiniai 20 ivykiu is /opt/aukcionas/voicebox/ivr.log."""
    events = []
    try:
        if IVR_LOG.is_file():
            lines = IVR_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-20:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    events.append({"laikas": "", "ivykis": "raw", "tekstas": line[:300]})
    except Exception as exc:
        log_event("log_klaida", klaida=type(exc).__name__)
    if not events:
        events = list(_events)[-20:]
    return JSONResponse({"ok": True, "count": len(events), "ivykiai": events})

