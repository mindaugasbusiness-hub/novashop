# -*- coding: utf-8 -*-
"""Penktadienio aukcionas - pilnai savarankiska aukciono svetaine.
V3: tvarkingas pardavejo (administratoriaus) skydelis su preku eile.
Preke pridedama per web forma - jei nera gyvo loto, paskelbiama is karto,
jei yra - automatiskai atsiduria eileje ir prasideda, kai baigiasi ankstesnis.
"""
import os
import sqlite3
import time
import uuid
import shutil
import threading
import hashlib
import json
import asyncio
import re
import urllib.request
import urllib.error
from urllib.parse import quote, urlencode
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response, FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(os.environ.get("AUKCIONAS_DATA_DIR", Path(__file__).resolve().parent))
PHOTOS_DIR = Path(os.environ.get("AUKCIONAS_PHOTOS_DIR", BASE_DIR / "photos"))
TTS_CACHE_DIR = BASE_DIR / "tts_cache"
DB_PATH = BASE_DIR / "aukcionas.db"
VILKAS_STAGE_FILE = BASE_DIR / "vilkas_stage_on.txt"
DESK_SONG_FILE = BASE_DIR / "desk_song.txt"
DESK_SONGS_DIR = Path(
    os.environ.get("AUKCIONAS_DESK_SONGS_DIR", BASE_DIR / "desk_songs")
)
MUZIKA_NOTEPAD_FILE = BASE_DIR / "patinkancios_muzikos_notepad.txt"
ADMIN_REG_DIR = BASE_DIR / "admin_registracijos"

# Šokėja VIENA visiems ekranams (serveris nusprendžia, klientai seka).
# PC ir telefonas mato tą pačią — ne atskirus localStorage deck.
DANCER_EXCLUDED_IDS = {13, 16}


def _available_dancer_urls() -> list[str]:
    found = []
    for path in PHOTOS_DIR.glob("dance_club_*.mp4"):
        match = re.fullmatch(r"dance_club_(\d+)\.mp4", path.name)
        try:
            usable = bool(match) and path.is_file() and path.stat().st_size > 50_000
        except OSError:
            usable = False
        if not usable:
            continue
        dancer_id = int(match.group(1))
        if dancer_id not in DANCER_EXCLUDED_IDS:
            found.append((dancer_id, f"/photos/{path.name}"))
    if found:
        return [url for _, url in sorted(found)]
    return [
        f"/photos/dance_club_{i}.mp4"
        for i in range(1, 16)
        if i not in DANCER_EXCLUDED_IDS
    ]


DANCER_URLS = _available_dancer_urls()
DANCER_ROTATE_S = 150  # auto keitimas kas ~2.5 min — visiems vienu metu
DANCER_STATE_FILE = BASE_DIR / "dancer_state.json"
DANCER_NEXT_MIN_S = 3  # F5 spam apsauga


def _dancer_read_state():
    try:
        d = json.loads(DANCER_STATE_FILE.read_text(encoding="utf-8") or "{}")
        idx = int(d.get("idx") or 0)
        at = float(d.get("at") or 0)
    except Exception:
        idx, at = 0, 0.0
    return idx, at


def _dancer_write_state(idx: int, at: float) -> None:
    try:
        DANCER_STATE_FILE.write_text(
            json.dumps({"idx": int(idx), "at": float(at)}), encoding="utf-8"
        )
    except Exception as e:
        print(f"[dancer] write fail: {e}", flush=True)


def get_dancer_public():
    """Dabartinė šokėja visiems. Auto-rotacija pagal laiką, be localStorage skirtumų."""
    now = time.time()
    total = len(DANCER_URLS)
    idx, at = _dancer_read_state()
    if at <= 0:
        at = now
    idx = idx % total
    steps = int((now - at) // DANCER_ROTATE_S) if now >= at else 0
    if steps > 0:
        idx = (idx + steps) % total
        at = at + steps * DANCER_ROTATE_S
        _dancer_write_state(idx, at)
    elif at > now:
        _dancer_write_state(idx, now)
        at = now
    url = DANCER_URLS[idx % total]
    return {"url": url, "n": (idx % total) + 1, "total": total, "idx": idx % total}


def dancer_next_public():
    now = time.time()
    total = len(DANCER_URLS)
    idx, at = _dancer_read_state()
    if now - float(at or 0) < DANCER_NEXT_MIN_S:
        return get_dancer_public()
    idx = (int(idx) + 1) % total
    _dancer_write_state(idx, now)
    url = DANCER_URLS[idx]
    return {"url": url, "n": idx + 1, "total": total, "idx": idx}

# Paspaudžiamos dainos (Desktop\Muzika → desk_songs\NN.webm). 0 = klubinis radijas.
DESK_SONG_TITLES = {
    2: "Blu Cantrell & Sean Paul — Breathe",
    3: "Britney Spears — Toxic",
    4: "PA69 — Biertornado",
    6: "Eric Prydz — Call On Me",
    7: "DMX — Party Up (Up In Here)",
    8: "Hugel & Solto — Jamaican (Bam Bam)",
    9: "Safri Duo — Played-A-Live",
    10: "Steve Angello & Laidback Luke — Show Me Love",
    11: "Stromae — Alors On Danse",
    12: "Hugel & Imael Angel & Ultra Nate - Movin",
    13: "Majestic & Boney M. — Rasputin",
    14: "Ely Oaks — Running Around",
    16: "Katy Perry — Firework",
    17: "LMFAO — Sexy And I Know It",
    18: "Justin Bieber & Nicki Minaj — Beauty And A Beat",
    19: "David Guetta & Kid Cudi — Memories",
    20: "Flo Rida — Whistle",
    21: "Crazy Town — Butterfly",
    22: "Drunken Masters & Ikkimel — Kein Kokain",
    23: "Ski Aggu & Sira — Mietfrei",
    24: "Beyonce & Jay-Z — Crazy In Love",
    25: "Eminem — The Real Slim Shady",
    26: "Edward Maya & Vika Jigulina — Stereo Love",
    27: "David Guetta — Sexy Bitch",
    28: "DJ Kool — Let Me Clear My Throat",
    29: "Missy Elliott — Lose Control",
    30: "Shirin David — Bauch Beine Po",
    31: "Reel 2 Real — I Like To Move It",
    32: "Vito Melor - Molchi",
}


def get_desk_song_n() -> int:
    try:
        n = int((DESK_SONG_FILE.read_text(encoding="utf-8") or "0").strip() or "0")
    except Exception:
        return 0
    return n if n in DESK_SONG_TITLES else 0


def set_desk_song_n(n: int) -> None:
    try:
        n = int(n or 0)
        if n and n not in DESK_SONG_TITLES:
            n = 0
        DESK_SONG_FILE.write_text(str(n), encoding="utf-8")
    except Exception as e:
        print(f"[desk_song] write fail: {e}", flush=True)


def desk_song_path(n: int) -> Path | None:
    p = DESK_SONGS_DIR / f"{int(n):02d}.webm"
    try:
        if p.is_file() and p.stat().st_size > 50_000:
            return p
    except Exception:
        return None
    return None


def desk_song_public() -> dict | None:
    n = get_desk_song_n()
    if n <= 0:
        return None
    return {"n": n, "title": DESK_SONG_TITLES.get(n) or f"Daina {n}", "url": f"/desk-songs/{n}"}


def desk_song_available_ns() -> list[int]:
    return [n for n in sorted(DESK_SONG_TITLES.keys()) if desk_song_path(n)]


def next_desk_song_n() -> int:
    """Kita daina po dabartinės (aplinka ratu). Jokio to paties failo iš eilės, jei yra kitų."""
    nums = desk_song_available_ns()
    if not nums:
        return 0
    cur = get_desk_song_n()
    if cur not in nums:
        return nums[0]
    if len(nums) == 1:
        return nums[0]
    return nums[(nums.index(cur) + 1) % len(nums)]



def get_vilkas_stage_on() -> bool:
    """Įžangos viršelis kol Vilkas neįjungtas (default OFF)."""
    try:
        return VILKAS_STAGE_FILE.read_text(encoding="utf-8").strip() == "1"
    except Exception:
        return False


def set_vilkas_stage_on(on: bool) -> None:
    try:
        VILKAS_STAGE_FILE.write_text("1" if on else "0", encoding="utf-8")
    except Exception as e:
        print(f"[vilkas_stage] write fail: {e}", flush=True)
ADMIN_PASSWORD = os.environ.get("AUKCIONAS_ADMIN_SLAPTAZODIS", "Ciulpkbybivafli1")
# Mokėjimo paskyros — TIK serverio pusėje / adminui / laimėtojui. Viešai nerodomos.
PAY_METHODS = ("paypal", "skrill", "neteller", "paysafe")
PAY_DEST = {
    "paypal": {
        "label": "PayPal",
        "email": "mindaugas.grinius2026@outlook.com",
        "hint": "Iš savo PayPal perveskite į nurodytą PayPal el. paštą. Paskirtyje — slapyvardis ir loto pavadinimas.",
    },
    "skrill": {
        "label": "Skrill",
        "email": "mindaugasbusiness@gmail.com",
        "hint": "Iš savo Skrill perveskite į nurodytą Skrill el. paštą. Paskirtyje — slapyvardis ir loto pavadinimas.",
    },
    "neteller": {
        "label": "Neteller",
        "email": "mindaugasbusiness@gmail.com",
        "hint": "Iš savo Neteller perveskite į nurodytą Neteller el. paštą. Paskirtyje — slapyvardis ir loto pavadinimas.",
    },
    "paysafe": {
        "label": "Paysafe",
        "email": "mindaugasbusiness@gmail.com",
        "hint": "Kodą įkelkite į SAVO Paysafe, tada perveskite. PIN nesiųskite. Paskirtyje — slapyvardis ir loto pavadinimas.",
    },
}
ELEVENLABS_API_KEY = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
ELEVENLABS_VOICE_ID = (os.environ.get("ELEVENLABS_VOICE_ID") or "Ex8Av2KSONaJNXHle6XJ").strip()  # NAUJAS_v3_lt (Vilkas 3/4)
# PATVIRTINTA: eleven_v3 + language_code=lt. NIEKADA multilingual_v2 (latviškas).
ELEVENLABS_MODELS = [
    m.strip()
    for m in (os.environ.get("ELEVENLABS_MODELS") or "eleven_v3").split(",")
    if m.strip()
] or ["eleven_v3"]
# Produkcijoje vienas balsas: tik dabartinis lokalus Vilkas 8.
# Seni serverio ENV ir MP3 kešai negali perjungti balso į ankstesnę versiją.
TTS_AUDIO_VER = "v8-lt-clear-20261007-r3"
TTS_PROVIDER = "vilkas"
EDGE_VOICE = (os.environ.get("EDGE_VOICE") or "lt-LT-LeonasNeural").strip()
EDGE_RATE = (os.environ.get("EDGE_RATE") or "-2%").strip()  # +12% tada +4% (-18→-2)
EDGE_PITCH = (os.environ.get("EDGE_PITCH") or "-4Hz").strip()


# --- VILKAS LOCAL TTS (be ElevenLabs mokesciu) ---
VILKAS_LOCAL_TTS_URL = (os.environ.get("VILKAS_LOCAL_TTS_URL") or "http://127.0.0.1:8765").strip().rstrip("/")
VILKAS_LOCAL_TTS_FIRST = True
VILKAS_LOCAL_ONLY = True


V8_TTS_AUDIO_VERS = [
    v.strip()
    for v in (os.environ.get("V8_TTS_AUDIO_VERS") or "v3lt56-vilkas4,v3lt55").split(",")
    if v.strip()
]


def _norm_speed(fast: bool, speed: float | None) -> float:
    # Ryški LT +12% tada +4% (0.88→~1.03)
    if speed is None:
        speed = 1.0 if fast else float(os.environ.get("TTS_SPEED") or 1.03)
    try:
        speed = float(speed)
    except Exception:
        speed = 1.03
    return max(0.75, min(1.15, speed))


def _soft_trim(text: str, max_len: int) -> str:
    """Nekirpti žodžio viduryje — TTS kitaip murma / nukerta galūnę."""
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    cut = t[: max_len]
    for sep in (". ", "! ", "? ", "; ", ", ", " "):
        i = cut.rfind(sep)
        if i >= max(40, max_len // 3):
            cut = cut[: i + (1 if sep.strip() else 0)].rstrip(" ,;")
            break
    else:
        cut = cut.rsplit(" ", 1)[0] if " " in cut else cut
    cut = cut.rstrip(" ….")
    if cut and cut[-1] not in ".!?":
        cut += "."
    return cut


def _v8_cached_audio(text: str, fast: bool, speed: float | None) -> bytes | None:
    """Tikras VILKAS_8 balsas, jau sugeneruotas anksčiau (ElevenLabs neliečiamas)."""
    sp = _norm_speed(fast, speed)
    for ver in V8_TTS_AUDIO_VERS:
        for f in (int(fast), 1 - int(fast)):
            key = hashlib.sha1(
                f"{ver}|{ELEVENLABS_VOICE_ID}|{ELEVENLABS_MODELS[0]}|lt|stab55|sim85|fast_{f}|speed_{sp}|{text}".encode("utf-8")
            ).hexdigest()
            p = TTS_CACHE_DIR / f"{key}.mp3"
            if p.is_file() and p.stat().st_size > 0:
                return p.read_bytes()
    return None


def _learned_path(text: str, speed: float) -> Path:
    key = hashlib.sha1(f"vilkas_learned|{speed:.2f}|{text}".encode("utf-8")).hexdigest()
    return TTS_CACHE_DIR / f"loc_{key}.mp3"


def _vilkas_local_synthesize(text: str, timeout: float = 25.0, speed: float = 1.0) -> tuple[bytes | None, str]:
    """RO AI Vilkas TTS. Grazina (audio_bytes, media_type)."""
    if not VILKAS_LOCAL_TTS_URL or not text.strip():
        return None, "audio/mpeg"
    body = json.dumps({"text": _soft_trim(text, 880), "speed": speed}).encode("utf-8")
    req = urllib.request.Request(
        f"{VILKAS_LOCAL_TTS_URL}/v1/speak",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "audio/wav, audio/mpeg, application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "audio/mpeg").split(";")[0].strip().lower()
            raw = resp.read()
            if raw and ctype.startswith("audio/"):
                return raw, ctype
            return None, "audio/mpeg"
    except Exception as e:
        print(f"[vilkas-local] FAIL: {type(e).__name__}: {e}")
        return None, "audio/mpeg"

# 1 = pirkimas/statymas IŠJUNGTA (ruošiama); 0 = galima pirkti
AUCTION_LOCKED = (os.environ.get("AUCTION_LOCKED") or "0").strip().lower() in ("1", "true", "yes", "on")
AUCTION_LOCK_MSG = (
    os.environ.get("AUCTION_LOCK_MSG")
    or "Pirkimas ir statymai laikinai išjungti. Registruotis jau galima — netrukus atidarysime statymus."
).strip()
# Tikra vieša registracija UŽDARYTA — mokosi imitaciniai pirkėjai (Mindaugo OK 2026-10-09).
PUBLIC_REGISTRATION_OPEN = (os.environ.get("PUBLIC_REGISTRATION_OPEN") or "0").strip().lower() in (
    "1", "true", "yes", "on"
)
PUBLIC_REG_CLOSED_MSG = (
    os.environ.get("PUBLIC_REG_CLOSED_MSG")
    or "Registracija laikinai uždaryta. Vyksta Vilko mokymosi praktika — tik imitaciniai pirkėjai."
).strip()
PRACTICE_BOTS = (os.environ.get("PRACTICE_BOTS") or "1").strip().lower() in ("1", "true", "yes", "on")
try:
    PRACTICE_BOT_COUNT = max(50, min(5000, int(os.environ.get("PRACTICE_BOT_COUNT") or "500")))
except Exception:
    PRACTICE_BOT_COUNT = 500
# F9/F10 — TIK Mindaugas. Praktika NEGALI pati įjungti scenos (F10 kitaip „neužsilaiko”).
# Jei kada reikės auto-ON mokymui: PRACTICE_AUTO_STAGE=1 env — bet F10 vis tiek laimi (žr. _practice_loop).
PRACTICE_AUTO_STAGE = (os.environ.get("PRACTICE_AUTO_STAGE") or "0").strip().lower() in (
    "1", "true", "yes", "on"
)
BACKGROUND_LOOPS_ENABLED = (
    os.environ.get("AUKCIONAS_DISABLE_BACKGROUND") or "0"
).strip().lower() not in ("1", "true", "yes", "on")

for d in (BASE_DIR, PHOTOS_DIR, TTS_CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

STEP_TIERS = [(10, 1), (30, 5), (float("inf"), 10)]
COUNTDOWN_S = 60
STARTUP_COUNTDOWN_S = int(os.environ.get("STARTUP_COUNTDOWN_S") or 75)
# F9 vakaro startas: welcome → tylos kava → pirmas lotas (sekundės)
OPENING_COFFEE_S = max(60, int(os.environ.get("OPENING_COFFEE_S") or 120))
# Po „Parduota“ paliekame trumpą scenos pauzę: gongas, sveikinimas, kava.
QUEUE_GAP_S = max(8, int(os.environ.get("QUEUE_GAP_S") or 8))


# Vienas paspaudimas visada kelia lygiai 1 €, nepriklausomai nuo seno serverio ENV.
BID_STEP = 1.0


def step_for(price):
    return BID_STEP


def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return con


def init_db():
    con = db()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_number INTEGER,
            title TEXT,
            description TEXT,
            photo_file TEXT,
            starting_price REAL,
            current_price REAL,
            shipping REAL,
            current_bidder TEXT,
            starts_at REAL,
            ends_at REAL,
            status TEXT DEFAULT 'live',
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER,
            name TEXT,
            amount REAL,
            at REAL
        );
        CREATE TABLE IF NOT EXISTS participants (
            pid TEXT PRIMARY KEY,
            name TEXT,
            nickname TEXT,
            contact TEXT,
            at REAL
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority INTEGER NOT NULL DEFAULT 50,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            expires_at REAL,
            unique_key TEXT UNIQUE
        );
        CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
        CREATE TABLE IF NOT EXISTS client_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at REAL NOT NULL,
            message TEXT NOT NULL,
            source TEXT,
            line INTEGER,
            column_no INTEGER,
            stack TEXT,
            user_agent TEXT
        );
        """
    )
    # migracijos senoms lentelems
    for stmt in (
        "ALTER TABLE lots ADD COLUMN starts_at REAL",
        "ALTER TABLE lots ADD COLUMN queue_order INTEGER",
        "ALTER TABLE lots ADD COLUMN resolved_at REAL",
        "ALTER TABLE lots ADD COLUMN pluses TEXT",
        "ALTER TABLE lots ADD COLUMN defects TEXT",
        "ALTER TABLE lots ADD COLUMN included TEXT",
        "ALTER TABLE lots ADD COLUMN condition TEXT",
        "ALTER TABLE participants ADD COLUMN nickname TEXT",
        "ALTER TABLE participants ADD COLUMN pay_method TEXT",
        "ALTER TABLE participants ADD COLUMN phone TEXT",
    ):
        try:
            con.execute(stmt)
        except sqlite3.OperationalError:
            pass
    con.commit()
    con.close()


def _normalize_pay_method(value: str | None) -> str:
    m = (value or "").strip().lower()
    if m not in PAY_METHODS:
        raise HTTPException(400, "pasirinkite mokėjimo būdą: PayPal, Skrill, Neteller arba Paysafe")
    return m


def _looks_like_email(value: str) -> bool:
    v = (value or "").strip()
    at = v.find("@")
    return at > 0 and "." in v[at + 1 :]


def _normalize_phone(value: str | None) -> str:
    raw = (value or "").strip()[:32]
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 8:
        raise HTTPException(400, "įveskite telefono numerį (pvz. +37066331913)")
    return raw


def _unique_public_nickname(con, preferred: str) -> str:
    """Jei Jonas jau yra — antras tampa Jonas2, tada Jonas3… (aukcione unikalus)."""
    base = re.sub(r"\s+", " ", (preferred or "").strip())[:20] or "Dalyvis"
    taken = set()
    for r in con.execute(
        "SELECT COALESCE(NULLIF(TRIM(nickname),''), TRIM(name)) AS pub FROM participants"
    ).fetchall():
        pub = (r["pub"] or "").strip().lower()
        if pub:
            taken.add(pub)
        # ir pirmas žodis iš pilno vardo (seni įrašai be slapyvardžio)
        first = pub.split()[0] if pub else ""
        if first:
            taken.add(first)
    cand = base
    n = 2
    while cand.lower() in taken:
        suf = str(n)
        cand = (base[: max(1, 24 - len(suf))] + suf)[:24]
        n += 1
        if n > 9999:
            cand = (base[:10] + uuid.uuid4().hex[:6])[:24]
            break
    return cand


def _email_domain(contact: str) -> str:
    v = (contact or "").strip().lower()
    if "@" not in v:
        return ""
    return v.split("@", 1)[1].strip()


def _html_esc(s) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _participant_admin_row(r) -> dict:
    contact = (r["contact"] if "contact" in r.keys() else "") or ""
    at = float(r["at"] or 0) if "at" in r.keys() else 0.0
    pay = (r["pay_method"] if "pay_method" in r.keys() else "") or ""
    phone = (r["phone"] if "phone" in r.keys() else "") or ""
    return {
        "pid": r["pid"],
        "name": r["name"] or "",
        "nickname": (r["nickname"] if "nickname" in r.keys() else "") or "",
        "contact": contact,
        "phone": phone,
        "email_domain": _email_domain(contact),
        "pay_method": pay,
        "at": at,
        "at_lt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(at)) if at else "",
        "is_demo": contact.strip().lower() == "demo",
    }


def _list_registrations(con, include_demo: bool = False) -> list[dict]:
    rows = con.execute(
        "SELECT pid, name, nickname, contact, phone, pay_method, at FROM participants ORDER BY at DESC"
    ).fetchall()
    out = []
    for r in rows:
        item = _participant_admin_row(r)
        if item["is_demo"] and not include_demo:
            continue
        out.append(item)
    return out


def _rebuild_admin_registracijos_files(extra: dict | None = None) -> None:
    """Atnaujina Desktop/serverio admin_registracijos failus iš DB."""
    try:
        ADMIN_REG_DIR.mkdir(parents=True, exist_ok=True)
        con = db()
        people = _list_registrations(con, include_demo=False)
        all_people = _list_registrations(con, include_demo=True)
        con.close()
        if extra:
            # ką tik įrašytas gali dar nebūti matomas — užtikrinam paskutinį
            pid = extra.get("pid")
            if pid and not any(p.get("pid") == pid for p in people):
                people.insert(0, extra)
                all_people.insert(0, extra)

        (ADMIN_REG_DIR / "visi.json").write_text(
            json.dumps({"updated": time.strftime("%Y-%m-%d %H:%M:%S"), "count": len(people), "people": people}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if extra:
            with (ADMIN_REG_DIR / "nauji.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(extra, ensure_ascii=False) + "\n")

        domains: dict[str, int] = {}
        for p in people:
            d = p.get("email_domain") or "(nėra)"
            domains[d] = domains.get(d, 0) + 1
        dom_lines = [f"Domenai ({len(domains)}) — atnaujinta {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
        for d, n in sorted(domains.items(), key=lambda x: (-x[1], x[0])):
            dom_lines.append(f"{n:4d}  {d}")
        (ADMIN_REG_DIR / "domenai.txt").write_text("\n".join(dom_lines) + "\n", encoding="utf-8")

        csv_lines = ["at_lt;name;nickname;contact;phone;email_domain;pay_method;pid"]
        for p in people:
            csv_lines.append(
                ";".join(
                    [
                        p.get("at_lt") or "",
                        (p.get("name") or "").replace(";", ","),
                        (p.get("nickname") or "").replace(";", ","),
                        (p.get("contact") or "").replace(";", ","),
                        (p.get("phone") or "").replace(";", ","),
                        p.get("email_domain") or "",
                        p.get("pay_method") or "",
                        p.get("pid") or "",
                    ]
                )
            )
        (ADMIN_REG_DIR / "visi.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

        rows_html = []
        for p in people:
            rows_html.append(
                "<tr>"
                f"<td>{_html_esc(p.get('at_lt'))}</td>"
                f"<td>{_html_esc(p.get('name'))}</td>"
                f"<td>{_html_esc(p.get('nickname'))}</td>"
                f"<td>{_html_esc(p.get('contact'))}</td>"
                f"<td>{_html_esc(p.get('phone'))}</td>"
                f"<td><b>{_html_esc(p.get('email_domain'))}</b></td>"
                f"<td>{_html_esc(p.get('pay_method'))}</td>"
                f"<td style='font-size:11px;opacity:.7'>{_html_esc(p.get('pid'))}</td>"
                "</tr>"
            )
        html = f"""<!doctype html><html lang="lt"><head><meta charset="utf-8">
<title>Registracijos · administracija</title>
<style>
body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#14100c;color:#f3ead9;padding:24px}}
h1{{font-size:22px;margin:0 0 6px}}
.sub{{color:#9a8b74;margin:0 0 18px;font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{border-bottom:1px solid #40331f;padding:8px 10px;text-align:left;vertical-align:top}}
th{{color:#b9a88f;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
tr:hover td{{background:#1f1811}}
.badge{{display:inline-block;background:#2a2018;border:1px solid #40331f;border-radius:8px;padding:4px 10px;margin:0 8px 12px 0;font-size:12px}}
</style></head><body>
<h1>Užsiregistravę žmonės</h1>
<p class="sub">Atnaujinta {time.strftime('%Y-%m-%d %H:%M:%S')} · realūs: {len(people)} · su demo: {len(all_people)}</p>
<div class="badge">domenų: {len(domains)}</div>
<div class="badge">failai: visi.json · visi.csv · domenai.txt · nauji.jsonl</div>
<table>
<thead><tr><th>Laikas</th><th>Vardas</th><th>Slapyvardis</th><th>El. paštas</th><th>Tel.</th><th>Domenas</th><th>Mokėjimas</th><th>PID</th></tr></thead>
<tbody>
{''.join(rows_html) if rows_html else '<tr><td colspan="8">Kol kas nėra registracijų.</td></tr>'}
</tbody></table>
</body></html>"""
        (ADMIN_REG_DIR / "sarasas.html").write_text(html, encoding="utf-8")
    except Exception as e:
        print(f"[admin_registracijos] rebuild fail: {e}", flush=True)


def _winner_pay_payload(con, lot) -> dict | None:
    """Privati laimėtojo mokėjimo info (adminui / pačiam laimėtojui)."""
    if not lot or lot.get("status") != "ended" or not lot.get("current_bidder"):
        return None
    nick = (lot.get("current_bidder") or "").strip()
    row = con.execute(
        "SELECT pid, name, nickname, contact, pay_method FROM participants "
        "WHERE COALESCE(NULLIF(nickname,''), name)=? ORDER BY at DESC LIMIT 1",
        (nick,),
    ).fetchone()
    if not row:
        return None
    method = (row["pay_method"] or "").strip().lower()
    dest = PAY_DEST.get(method) or {}
    total = round(float(lot.get("current_price") or 0) + float(lot.get("shipping") or 0), 2)
    return {
        "lot_id": lot.get("id"),
        "lot_number": lot.get("lot_number"),
        "lot_title": lot.get("title"),
        "winner_name": row["name"],
        "winner_nickname": row["nickname"] or nick,
        "winner_contact": row["contact"],
        "pay_method": method,
        "pay_label": dest.get("label") or method.upper(),
        "pay_email": dest.get("email") or "",
        "pay_hint": dest.get("hint") or "",
        "amount": float(lot.get("current_price") or 0),
        "shipping": float(lot.get("shipping") or 0),
        "total": total,
    }


init_db()

# Po kiekvieno deploy/restart — naujas ID; lankytojas automatiškai gauna šviežią puslapį
try:
    _app_mtime = int(Path(__file__).stat().st_mtime)
except Exception:
    _app_mtime = 0
BUILD_ID = f"{_app_mtime}-{int(time.time())}"

NO_CACHE_HEADERS = {
    "Cache-Control": "private, no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "CDN-Cache-Control": "no-store",
    "Cloudflare-CDN-Cache-Control": "no-store",
    "Surrogate-Control": "no-store",
}

app = FastAPI()
app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")
from ivr import router as ivr_router
app.include_router(ivr_router)


@app.middleware("http")
async def swiss_no_cache(request: Request, call_next):
    """Lankytojas įveda adresą — visada šviežias HTML/API (be Ctrl+F5)."""
    response = await call_next(request)
    path = request.url.path or "/"
    if path == "/" or path.startswith("/api/") or path.endswith(".html"):
        for k, v in NO_CACHE_HEADERS.items():
            response.headers[k] = v
    return response

EVENT_HISTORY_LIMIT = max(100, int(os.environ.get("EVENT_HISTORY_LIMIT") or 600))
CLIENT_ERROR_LIMIT = max(20, int(os.environ.get("CLIENT_ERROR_LIMIT") or 200))


def _event_row(row):
    if not row:
        return None
    out = dict(row)
    try:
        out["payload"] = json.loads(out.get("payload") or "{}")
    except Exception:
        out["payload"] = {}
    return out


def emit_event(event_type, payload=None, priority=50, ttl=120, unique_key=None, con=None):
    """Vienintelis autoritetingas scenos įvykių šaltinis."""
    own = con is None
    dbc = con or db()
    now = time.time()
    expires = now + max(1, ttl) if ttl else None
    try:
        cur = dbc.execute(
            "INSERT OR IGNORE INTO events(priority,event_type,payload,created_at,expires_at,unique_key) "
            "VALUES(?,?,?,?,?,?)",
            (int(priority), str(event_type)[:50], json.dumps(payload or {}, ensure_ascii=False),
             now, expires, unique_key),
        )
        event_id = cur.lastrowid if cur.rowcount else None
        if event_id:
            dbc.execute(
                "DELETE FROM events WHERE event_id <= "
                "(SELECT COALESCE(MAX(event_id),0)-? FROM events)",
                (EVENT_HISTORY_LIMIT,),
            )
        if own:
            dbc.commit()
        if not event_id:
            return None
        return {
            "event_id": event_id, "priority": int(priority), "event_type": event_type,
            "payload": payload or {}, "created_at": now, "expires_at": expires,
        }
    finally:
        if own:
            dbc.close()


def events_since(last_event_id=0, limit=200):
    now = time.time()
    con = db()
    rows = con.execute(
        "SELECT event_id,priority,event_type,payload,created_at,expires_at FROM events "
        "WHERE event_id>? AND (expires_at IS NULL OR expires_at>?) "
        "ORDER BY event_id ASC LIMIT ?",
        (max(0, int(last_event_id or 0)), now, min(500, max(1, int(limit)))),
    ).fetchall()
    con.close()
    return [_event_row(r) for r in rows]


def latest_event_id():
    con = db()
    row = con.execute("SELECT COALESCE(MAX(event_id),0) AS n FROM events").fetchone()
    con.close()
    return int(row["n"] or 0)


def get_active_lot(con):
    row = con.execute(
        "SELECT * FROM lots WHERE status='live' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        return dict(row)
    # trumpa "malones" pauze: kai lotas ka tik baigtas (rankiniu budu ar
    # savaime), rodome ji dar QUEUE_GAP_S sekundziu kaip "aktyvu" (status
    # ended), kad pirkejo puslapis suspetu parodyti PARDUOTA / sventine
    # animacija, o ne is karto dingtu is akiu
    row = con.execute(
        "SELECT * FROM lots WHERE status='ended' AND resolved_at IS NOT NULL "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row and time.time() - row["resolved_at"] < QUEUE_GAP_S:
        return dict(row)
    return None


def get_live_lot(con):
    """Tik tikrai vykstantis (status='live') lotas - be malones periodo.
    Naudojama ten, kur sprendziama, ar galima leisti nauja lota is karto
    (o ne get_active_lot, kuri malones metu grazina ir ka tik pasibaigusi)."""
    row = con.execute(
        "SELECT * FROM lots WHERE status='live' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def get_past_lots(con, limit=8, exclude_id=None):
    rows = con.execute(
        "SELECT * FROM lots WHERE status='ended' ORDER BY id DESC LIMIT ?", (limit + 1,)
    ).fetchall()
    out = [dict(r) for r in rows if r["id"] != exclude_id]
    return out[:limit]


def get_queue(con):
    rows = con.execute(
        "SELECT * FROM lots WHERE status='queued' ORDER BY queue_order ASC"
    ).fetchall()
    return [dict(r) for r in rows]


def _lot_preview(row):
    """Vieša kortelė karusele — nuotrauka, kaina, defektai, eilė."""
    d = dict(row) if row else {}
    return {
        "id": d.get("id"),
        "title": d.get("title") or "",
        "photo_file": d.get("photo_file"),
        "starting_price": d.get("starting_price"),
        "current_price": d.get("current_price"),
        "defects": (d.get("defects") or "").strip(),
        "condition": (d.get("condition") or "").strip(),
        "pluses": (d.get("pluses") or "").strip(),
        "included": (d.get("included") or "").strip(),
        "shipping": d.get("shipping"),
        "status": d.get("status"),
        "queue_order": d.get("queue_order"),
        "lot_number": d.get("lot_number"),
        "description": (d.get("description") or "").strip(),
    }


def maybe_end_lot(con, lot):
    # BE F9 (įžanga) lotai SUŠALDYTI — laikmatis nejuda, niekas nesibaigia savaime
    if not get_vilkas_stage_on():
        return lot
    if lot and lot["status"] == "live" and lot["ends_at"] and time.time() > lot["ends_at"]:
        if AUCTION_LOCKED:
            # Ruošimas — baigiasi BE pardavimo (nulinamas laimėtojas)
            con.execute(
                "UPDATE lots SET status='ended', current_bidder=NULL, resolved_at=? WHERE id=?",
                (time.time(), lot["id"]),
            )
        else:
            con.execute(
                "UPDATE lots SET status='ended', resolved_at=? WHERE id=?",
                (time.time(), lot["id"]),
            )
        con.commit()
        lot = dict(con.execute("SELECT * FROM lots WHERE id=?", (lot["id"],)).fetchone())
        winner = lot.get("current_bidder") or ""
        sold_payload = {
            "lot_id": lot["id"], "title": lot.get("title") or "",
            "winner": winner, "price": lot.get("current_price") or 0,
            "text": ("Parduota! Plojimai!" if winner else "Lotas baigtas be statymų."),
        }
        _round = int(float(lot.get("resolved_at") or time.time()))
        emit_event("sold", sold_payload, 100, 180, f"sold:{lot['id']}:{_round}", con=con)
        # Kitas lotas IŠKART — Vilkas turi pristatyti, ne kavos stovėti.
        nxt = None
        if not AUCTION_LOCKED:
            try:
                nxt = advance_to_next_lot_now(con)
            except Exception as e:
                print(f"[maybe_end] advance fail: {e}", flush=True)
        if nxt:
            if PRACTICE_BOTS:
                # Praktika: trumpa kava (ne 40s amžinybė) — tada lot_intro, kad suktųsi visos prekės
                try:
                    st = time.time() + 22.0
                    con.execute(
                        "UPDATE lots SET starts_at=?, ends_at=? WHERE id=?",
                        (st, st + float(COUNTDOWN_S), nxt["id"]),
                    )
                    con.commit()
                    nxt = dict(con.execute("SELECT * FROM lots WHERE id=?", (nxt["id"],)).fetchone())
                except Exception as e:
                    print(f"[maybe_end] practice delay fail: {e}", flush=True)
                coffee_lines = list(VILKAS8_COFFEE)
                emit_event(
                    "intermission",
                    {
                        "lot_id": lot["id"],
                        "text": coffee_lines[int(_round) % len(coffee_lines)],
                        "skip_coffee": False,
                    },
                    48, 45, f"intermission:{lot['id']}:{_round}", con=con,
                )
                emit_event(
                    "joke",
                    {
                        "lot_id": lot["id"],
                        **_vp(
                            "joke",
                            int(lot["id"]) + 88,
                            VILKAS8_JOKES
                            + ["Opa opa! Kas gėrė kavą — tas kelia kainą smagiau!"],
                        ),
                    },
                    42, 35, f"joke_break:{lot['id']}:{_round}", con=con,
                )
            else:
                # Tikra prekyba: trumpas tiltas — be ilgos kavos; intro IŠKART
                emit_event(
                    "intermission",
                    {
                        "lot_id": lot["id"],
                        "text": "Dėmesio — kitas lotas!",
                        "skip_coffee": True,
                    },
                    40, 12, f"intermission:{lot['id']}:{_round}", con=con,
                )
                try:
                    intro_uk = f"lot_intro:{nxt['id']}:{int(float(nxt.get('starts_at') or 0))}"
                    emit_event(
                        "lot_intro",
                        {
                            "lot_id": nxt["id"],
                            "lot_number": nxt.get("lot_number"),
                            "title": nxt.get("title") or "",
                            "text": _lot_intro_text(nxt),
                            "starts_at": nxt.get("starts_at"),
                        },
                        70, max(120, STARTUP_COUNTDOWN_S + 60), intro_uk, con=con,
                    )
                except Exception as e:
                    print(f"[maybe_end] lot_intro fail: {e}", flush=True)
        else:
            emit_event(
                "intermission",
                {"lot_id": lot["id"], "text": "Trumpa kavos pertrauka. Netrukus kitas lotas."},
                45, max(20, QUEUE_GAP_S + 10), f"intermission:{lot['id']}:{_round}", con=con,
            )
        con.commit()
    return lot


@app.get("/api/state")
def api_state():
    con = db()
    lot = get_active_lot(con)
    lot = maybe_end_lot(con, lot)
    bids = []
    if lot:
        rows = con.execute(
            "SELECT name, amount, at FROM bids WHERE lot_id=? ORDER BY at DESC LIMIT 20",
            (lot["id"],),
        ).fetchall()
        bids = [dict(r) for r in rows]
    past = get_past_lots(con, exclude_id=lot["id"] if lot else None)
    queue_rows = get_queue(con)
    queue = [_lot_preview(r) for r in queue_rows]
    queue_len = len(queue)
    queue_titles = [q["title"] for q in queue[:8]]
    pcount = con.execute("SELECT COUNT(*) c FROM participants").fetchone()["c"]
    pnames = []
    for r in con.execute(
        "SELECT COALESCE(NULLIF(nickname,''), name) AS public_name "
        "FROM participants ORDER BY at DESC LIMIT 200"
    ).fetchall():
        public_name = (r["public_name"] or "").strip()[:24]
        if public_name and public_name not in pnames:
            pnames.append(public_name)
    recent_joins = [
        {
            "pid": (r["pid"] or "").strip(),
            "name": (r["public_name"] or "").strip()[:24],
            "at": float(r["at"] or 0),
        }
        for r in con.execute(
            "SELECT pid, COALESCE(NULLIF(nickname,''), name) AS public_name, at "
            "FROM participants ORDER BY at DESC LIMIT 24"
        ).fetchall()
    ]
    con.close()
    # lot Row → dict (JSON) + taisyklinga LT ekrane
    lot_out = _pretty_lot(dict(lot)) if lot else None
    past = [_pretty_lot(p) for p in past]
    queue = [_pretty_lot(q) for q in queue]
    queue_titles = [q["title"] for q in queue[:8]]
    return {
        "lot": lot_out,
        "bids": bids,
        "past_lots": past,
        "participant_count": pcount,
        "participant_names": pnames[:120],
        "recent_joins": recent_joins,
        "queue": queue,
        "queue_len": queue_len,
        "queue_titles": queue_titles,
        "tts": "vilkas",
        "auction_locked": AUCTION_LOCKED,
        "auction_lock_msg": AUCTION_LOCK_MSG if AUCTION_LOCKED else "",
        "vilkas_stage_on": get_vilkas_stage_on(),
        "public_registration_open": PUBLIC_REGISTRATION_OPEN,
        "public_reg_closed_msg": "" if PUBLIC_REGISTRATION_OPEN else PUBLIC_REG_CLOSED_MSG,
        "practice_bots": PRACTICE_BOTS,
        "practice_bot_count": PRACTICE_BOT_COUNT if PRACTICE_BOTS else 0,
        "desk_song": desk_song_public(),
        "dancer": get_dancer_public(),
        "latest_event_id": latest_event_id(),
    }


@app.get("/api/events")
def api_events(last_event_id: int = 0):
    """Polling fallback eventams, kai WebSocket neprieinamas."""
    return {"events": events_since(last_event_id), "latest_event_id": latest_event_id()}


@app.websocket("/ws")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    try:
        raw_last = websocket.query_params.get("last_event_id", "0")
        last_id = max(0, int(raw_last or 0))
    except (TypeError, ValueError):
        last_id = 0
    try:
        while True:
            # Būsena PIRMIAU už eventus — kitaip F9 lot_intro ateina kol dar įžanga ir pradingsta
            await websocket.send_json({"kind": "state", "state": api_state()})
            batch = events_since(last_id)
            for event in batch:
                await websocket.send_json({"kind": "event", "event": event})
                last_id = max(last_id, int(event["event_id"]))
            await asyncio.sleep(0.45)
    except (WebSocketDisconnect, RuntimeError):
        return


@app.post("/api/client_error")
async def api_client_error(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    con = db()
    con.execute(
        "INSERT INTO client_errors(created_at,message,source,line,column_no,stack,user_agent) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            time.time(), str(body.get("message") or "client_error")[:1000],
            str(body.get("source") or "")[:500], int(body.get("line") or 0),
            int(body.get("column") or 0), str(body.get("stack") or "")[:5000],
            str(request.headers.get("user-agent") or "")[:500],
        ),
    )
    con.execute(
        "DELETE FROM client_errors WHERE id <= "
        "(SELECT COALESCE(MAX(id),0)-? FROM client_errors)",
        (CLIENT_ERROR_LIMIT,),
    )
    con.commit()
    con.close()
    return {"ok": True}


@app.post("/api/admin/client_errors")
async def api_admin_client_errors(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    con = db()
    rows = con.execute(
        "SELECT * FROM client_errors ORDER BY id DESC LIMIT ?", (CLIENT_ERROR_LIMIT,)
    ).fetchall()
    con.close()
    return {"ok": True, "errors": [dict(r) for r in rows]}


# Taisyklinga lietuvių kalba: Mindaugas dažnai rašo be lietuviškų raidžių
# ("sitas", "sviesus", "ibrezimas", "deze"). Vilkas turi SKAITYTI ir ekranas
# RODYTI taisyklingai. Žodynas: žemutinės formos → taisyklingos (case išlaikomas).
_LT_FIX_WORDS = {
    "sitas": "šitas", "sita": "šita", "sis": "šis", "si": "ši", "sie": "šie", "sios": "šios",
    "sviesus": "šviesus", "sviesi": "šviesi", "sviesiai": "šviesiai", "sviesos": "šviesos",
    "ibrezimas": "įbrėžimas", "ibrezimai": "įbrėžimai", "ibrezimu": "įbrėžimų", "ibrežimas": "įbrėžimas",
    "idauzimu": "įdaužimų", "idauzimas": "įdaužimas", "idauzimai": "įdaužimai", "iduzimu": "įdužimų",
    "nugarojeje": "nugarėlėje", "nugaroje": "nugarėlėje", "nugarele": "nugarėlė", "nugareles": "nugarėlės",
    "nugarelej": "nugarėlėje", "nugareleje": "nugarėlėje",
    "deze": "dėžė", "dezute": "dėžutė", "deklas": "dėklas", "adeklis": "įdėklas", "ideklas": "įdėklas",
    "bukle": "būklė", "nera": "nėra", "procentu": "procentų", "procentai": "procentai",
    "pradzia": "pradžia", "pradzioje": "pradžioje", "eura": "eurą",
    "gerbejams": "gerbėjams", "gerbejas": "gerbėjas", "matine": "matinė",
    "sklandziai": "sklandžiai", "preke": "prekė", "prekes": "prekės", "melynas": "mėlynas", "melyna": "mėlyna",
    "mazas": "mažas", "maza": "maža", "mazi": "maži", "mazu": "mažų",
    "aiskios": "aiškios", "aiskus": "aiškus", "aiski": "aiški", "aiskiai": "aiškiai",
    "skambuciams": "skambučiams", "skambuciai": "skambučiai",
    "zaidimams": "žaidimams", "zaidimai": "žaidimai", "zaidimas": "žaidimas", "zaidimu": "žaidimų",
    "visa diena": "visą dieną", "visa nakti": "visą naktį",
    "ausines": "ausinės", "ausiniu": "ausinių",
    "ikrautas": "įkrautas", "ikrovimas": "įkrovimas", "ijungiamas": "įjungiamas", "isjungiamas": "išjungiamas",
    "rimtu": "rimtų", "smulkus": "smulkūs", "smulkiu": "smulkių",
    "nusidevejes": "nusidėvėjęs", "nusideveje": "nusidėvėję", "nusidevejusi": "nusidėvėjusi",
    "itrukimas": "įtrūkimas", "itrukimu": "įtrūkimų", "itrukes": "įtrūkęs",
    "zmogui": "žmogui", "zmogus": "žmogus", "mociutei": "močiutei",
    "zalia": "žalia", "zalias": "žalias", "rozine": "rožinė", "rozinis": "rožinis",
    "sidabrine": "sidabrinė", "auksine": "auksinė",
    "krastas": "kraštas", "kraste": "krašte", "krastai": "kraštai", "remelis": "rėmelis", "remelio": "rėmelio",
    "sasaja": "sąsaja", "dulkems": "dulkėms",
    "pirstu": "pirštų", "pirstas": "pirštas",
    "korteles": "kortelės", "kortele": "kortelė",
    "svarus": "švarus", "svari": "švari",
    "ziemos": "žiemos", "ziema": "žiema",
    "nesiojamas": "nešiojamas", "plansete": "planšetė", "plansetes": "planšetės", "klaviatura": "klaviatūra", "pele": "pelė",
    "sazininga": "sąžininga", "saziningai": "sąžiningai",
    "istraukti": "ištraukti", "isirasyti": "įsirašyti", "irasyti": "įrašyti",
    "idejimas": "įdėjimas", "ideti": "įdėti", "isiusti": "išsiųsti", "issiusti": "išsiųsti",
    "uzsakymas": "užsakymas", "uzsakyti": "užsakyti", "uzsiregistruoti": "užsiregistruoti",
    "laimetojas": "laimėtojas", "laimetojui": "laimėtojui", "pirkejas": "pirkėjas", "pirkejai": "pirkėjai",
    "pardavejas": "pardavėjas", "siulyti": "siūlyti", "siulymas": "siūlymas", "siulykite": "siūlykite",
    "zinute": "žinutė", "zinutes": "žinutės", "pastas": "paštas", "pasto": "pašto", "pastu": "paštu",
    "apmokejimas": "apmokėjimas", "apmoketi": "apmokėti", "grazinimas": "grąžinimas", "grazinti": "grąžinti",
}
_LT_FIX_RE = re.compile(
    r"(?<![\w\u00C0-\u024F])(" + "|".join(sorted(map(re.escape, _LT_FIX_WORDS), key=len, reverse=True)) + r")(?![\w\u00C0-\u024F])",
    flags=re.I,
)


def _lt_fix(text: str) -> str:
    """Grąžina taisyklingą LT (šitas, šviesus, įbrėžimas…) — case išlaikomas."""
    if not text:
        return text or ""

    def rep(m):
        src = m.group(0)
        dst = _LT_FIX_WORDS.get(src.lower())
        if not dst:
            return src
        if src.isupper() and len(src) > 1:
            return dst.upper()
        if src[0].isupper():
            return dst[0].upper() + dst[1:]
        return dst

    t = _LT_FIX_RE.sub(rep, text)
    # Skaičius + euru (be lietuviškos ų) → eurų. Neliesti „vienu euru“.
    t = re.sub(r"\b(\d+)\s+euru\b", r"\1 eurų", t, flags=re.I)
    # Sugadintas fragmentas iš senų pavyzdžių: "euru nei pigiai nei brangiai. " / "euru solidi pradzia. "
    t = re.sub(r"^\s*(eur[uų]\s+(nei\s+pigiai\s+nei\s+brangiai|solidi\s+pradžia|solidi\s+pradzia))\.\s*", "", t, flags=re.I)
    return t


def _pretty_lot(d):
    """Ekranui: taisyklinga LT (šitas, šviesus, įbrėžimas) be TTS santrumpų."""
    if not d:
        return d
    out = dict(d)
    for k in ("title", "description", "pluses", "defects", "included"):
        if out.get(k):
            out[k] = _lt_fix(str(out[k]))
    return out


def _lt_eur(n: float) -> str:
    """Lietuviškas skaitvardžio + 'euras' derinimas: 1 euras, 2 eurai, 10 eurų, 21 euras, 25 eurai."""
    try:
        v = float(n or 0)
    except Exception:
        v = 0.0
    whole = int(round(v))
    if abs(v - whole) > 0.009:
        return f"{v:.2f}".replace(".", ",") + " euro"
    last2 = whole % 100
    last = whole % 10
    if 11 <= last2 <= 19 or last == 0:
        word = "eurų"
    elif last == 1:
        word = "euras"
    else:
        word = "eurai"
    return f"{whole} {word}"


def _calm_text(text: str) -> str:
    """Aiški bendrinė LT TTS — santrumpos išskleistos, pauzės, be nukirstų galūnių."""
    t = _lt_fix(text or "").replace("?!", "?").replace("!!", "!")
    t = t.replace("—", ", ").replace("–", ", ").replace("…", ".")
    # Santrumpos / angliški → lietuviški žodžiai (kitaip TTS murma)
    t = re.sub(r"\bUSB-?C\b", "ju es bi si", t, flags=re.I)
    t = re.sub(r"\bFace\s*ID\b", "Feis ai di", t, flags=re.I)
    t = re.sub(r"\biPhone\b", "ai fonas", t, flags=re.I)
    t = re.sub(r"\bGalaxy\b", "Geleksi", t, flags=re.I)
    t = re.sub(r"\bSamsung\b", "Samsungas", t, flags=re.I)
    t = re.sub(r"\bApple\b", "Epl", t, flags=re.I)
    t = re.sub(r"\bSE\b", "es i", t)
    t = re.sub(r"\b(\d+)\s*GB\b", r"\1 gigabaitų", t, flags=re.I)
    t = re.sub(r"\b(\d+)\s*TB\b", r"\1 terabaitų", t, flags=re.I)
    t = re.sub(r"\b(\d+)\s*Hz\b", r"\1 hercų", t, flags=re.I)
    t = re.sub(r"\b(\d+)\s*%", r"\1 procentų", t)
    t = re.sub(r"\bS(\d{1,2})\b", r"es \1", t)  # S21 → es 21
    t = re.sub(r"\bLTE\b", "el te e", t)
    t = re.sub(r"\b5G\b", "penki gė", t, flags=re.I)
    t = re.sub(r"\b4G\b", "keturi gė", t, flags=re.I)
    t = re.sub(r"\bWi-?Fi\b", "vai fai", t, flags=re.I)
    t = re.sub(r"\bNFC\b", "en ef cė", t, flags=re.I)
    # Dialektas / slangas → bendrinė
    for a, b in (
        ("Nu ontin", "Na taip"),
        ("nu ontin", "na taip"),
        ("Kas tou par", "Kas per"),
        ("kas tou par", "kas per"),
        ("žmuogos", "žmogus"),
        ("Aba tu", "Na tu"),
        ("aba tu", "na tu"),
        ("tep i reik", "taip ir reikia"),
        ("Tep i reik", "Taip ir reikia"),
        ("kap daba bus", "kas dabar bus"),
        ("Išsitaliavuojau aš per jumis", "Vos nenusideginau"),
        ("Žemaitis nepasiduoda", "Tikras kovotojas"),
        ("Žemaičiai jau būtų", "Drąsuoliai jau būtų"),
        ("Kaip žemaitis sakytų — nebūk skūpus", "Nebūk skūpus"),
        ("ibrezimas", "įbrėžimas"),
        ("ibrežimas", "įbrėžimas"),
        ("deze", "dėžė"),
        ("bukle", "būklė"),
    ):
        t = t.replace(a, b)
    # Pauzės: kableliai / taškai aiškiau
    t = re.sub(r"\s*;\s*", ". ", t)
    t = re.sub(r"\s*/\s*", ", ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    if t and t[-1] not in ".!?":
        t += "."
    return t


def _edge_synthesize(text: str, fast: bool = False) -> bytes | None:
    """Atsarginis Edge TTS — naudojamas TIK kai TTS_PROVIDER=edge."""
    try:
        import asyncio
        import edge_tts
    except ImportError:
        return None
    if not text.strip():
        return None
    rate = EDGE_RATE if not fast else "+8%"
    pitch = EDGE_PITCH if not fast else "-2Hz"
    key = hashlib.sha1(f"edge|{EDGE_VOICE}|{rate}|{pitch}|{text}".encode("utf-8")).hexdigest()
    cached = TTS_CACHE_DIR / f"{key}.mp3"
    if cached.is_file() and cached.stat().st_size > 0:
        return cached.read_bytes()
    try:
        tmp = cached.with_suffix(".tmp")
        asyncio.run(edge_tts.Communicate(text[:900], EDGE_VOICE, rate=rate, pitch=pitch).save(str(tmp)))
        tmp.replace(cached)
        return cached.read_bytes()
    except Exception as e:
        print(f"[edge-tts] FAIL: {type(e).__name__}: {e}")
        return None


def _elevenlabs_synthesize(text: str, fast: bool = False, speed: float | None = None) -> bytes | None:
    """Sugeneruoja MP3 per ElevenLabs. Be rakto — None. Be Edge fallback."""
    if not ELEVENLABS_API_KEY or not text.strip():
        return None
    if speed is None:
        speed = 1.0 if fast else float(os.environ.get("TTS_SPEED") or 1.0)
    try:
        speed = float(speed)
    except Exception:
        speed = 1.0
    speed = max(0.7, min(1.2, speed))
    key = hashlib.sha1(
        f"{TTS_AUDIO_VER}|{ELEVENLABS_VOICE_ID}|{ELEVENLABS_MODELS[0]}|lt|stab55|sim85|fast_{int(fast)}|speed_{speed}|{text}".encode("utf-8")
    ).hexdigest()
    cached = TTS_CACHE_DIR / f"{key}.mp3"
    if cached.is_file() and cached.stat().st_size > 0:
        return cached.read_bytes()
    with _TTS_LOCKS_GUARD:
        lock = _TTS_LOCKS.setdefault(key, threading.Lock())
    with lock:
        if cached.is_file() and cached.stat().st_size > 0:
            return cached.read_bytes()
        return _elevenlabs_fetch(text, cached, fast=fast, speed=speed)


_TTS_LOCKS: dict = {}
_TTS_LOCKS_GUARD = threading.Lock()


def _elevenlabs_fetch(text: str, cached: Path, fast: bool = False, speed: float = 1.0) -> bytes | None:
    # Lietuvių kalba TIK su eleven_v3 + language_code=lt.
    # multilingual_v2 lietuvių nepalaiko → latviškas akcentas.
    spoken = _calm_text(text)[:900]
    last_err = None
    for attempt in range(3):
        for model_id in ELEVENLABS_MODELS:
            is_v3 = "eleven_v3" in model_id or model_id.endswith("_v3")
            if is_v3:
                # NAUJAS_v3_lt etalonas (vilkas_3 / VILKAS 4) — stability 0.55, similarity 0.85
                vs = {
                    "stability": 0.45 if fast else 0.55,
                    "similarity_boost": 0.85,
                }
            else:
                # Draudžiama produkcijoje — palikta tik jei ENV per klaidą
                vs = {
                    "stability": 0.72 if fast else 0.8,
                    "similarity_boost": 0.92,
                    "style": 0.08,
                    "use_speaker_boost": True,
                    "speed": speed,
                }
            payload = {
                "text": spoken,
                "model_id": model_id,
                "voice_settings": vs,
            }
            if is_v3:
                payload["language_code"] = "lt"
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=55) as resp:
                    audio = resp.read()
                if not audio:
                    raise RuntimeError("tuščias atsakymas")
                cached.write_bytes(audio)
                return audio
            except Exception as e:
                last_err = e
                print(f"[ElevenLabs] try={attempt+1} model={model_id} FAIL: {type(e).__name__}: {e}")
                continue
        time.sleep(0.35 * (attempt + 1))
    print(f"[ElevenLabs] VISI bandymai nepavyko (BE Edge fallback): {last_err}")
    return None


@app.get("/blues.mp3")
def api_blues():
    p = PHOTOS_DIR / "blues_slow_burn.mp3"
    if p.is_file():
        return FileResponse(p, media_type="audio/mpeg")
    return Response(status_code=404)


ILOVE_CHANNELS_URL = (
    "https://ilovemusic.de/typo3conf/ext/ep_channel/Scripts/channelSequence.php?pageuid=1"
)
_radio_now_cache: dict[str, tuple[float, dict]] = {}
_RADIO_NOW_TTL = 10.0


def _fetch_ilove_segment(segment: str) -> dict | None:
    segment = (segment or "").strip().lower()[:48]
    if not segment:
        return None
    now = time.time()
    cache_key = f"ilove:{segment}"
    cached = _radio_now_cache.get(cache_key)
    if cached and now - cached[0] < _RADIO_NOW_TTL:
        return cached[1]
    try:
        req = urllib.request.Request(
            ILOVE_CHANNELS_URL,
            headers={"User-Agent": "penktadienioaukcionas/1.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for ch in data:
            if (ch.get("segmentname") or "").lower() != segment:
                continue
            cur = ch.get("current") or {}
            cover = (cur.get("cover") or "").strip()
            if cover.startswith("/"):
                cover = f"https://ilovemusic.de{cover}"
            out = {
                "ok": True,
                "source": "ilovemusic",
                "station": ch.get("name") or segment,
                "artist": (cur.get("artist") or "").strip(),
                "title": (cur.get("title") or "").strip(),
                "cover": cover,
                "segment": segment,
            }
            _radio_now_cache[cache_key] = (now, out)
            return out
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "segment": segment}
    return {"ok": False, "error": "segment_not_found", "segment": segment}


def _fetch_icy_now(stream_url: str) -> dict | None:
    stream_url = (stream_url or "").strip()
    if not stream_url.startswith("https://"):
        return None
    now = time.time()
    cache_key = f"icy:{stream_url}"
    cached = _radio_now_cache.get(cache_key)
    if cached and now - cached[0] < _RADIO_NOW_TTL:
        return cached[1]
    try:
        req = urllib.request.Request(
            stream_url,
            headers={
                "Icy-MetaData": "1",
                "User-Agent": "Mozilla/5.0 (compatible; penktadienioaukcionas/1.0)",
                "Connection": "close",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta_int_raw = resp.headers.get("icy-metaint") or resp.headers.get("Icy-Metaint")
            if not meta_int_raw:
                return None
            meta_int = int(meta_int_raw)
            buf = b""
            need = meta_int + 512
            while len(buf) < need:
                chunk = resp.read(min(4096, need - len(buf)))
                if not chunk:
                    break
                buf += chunk
            if len(buf) <= meta_int:
                return None
            meta_len = buf[meta_int] * 16
            if meta_len <= 0:
                return None
            meta_bytes = buf[meta_int + 1 : meta_int + 1 + meta_len]
            meta_str = meta_bytes.decode("utf-8", errors="replace").strip("\x00")
            m = re.search(r"StreamTitle='([^']*)'", meta_str) or re.search(
                r'StreamTitle="([^"]*)"', meta_str
            )
            if not m:
                return None
            raw = m.group(1).strip()
            artist, title = raw, ""
            if " - " in raw:
                artist, title = [p.strip() for p in raw.split(" - ", 1)]
            out = {
                "ok": True,
                "source": "icy",
                "station": "",
                "artist": artist,
                "title": title,
                "raw": raw,
            }
            _radio_now_cache[cache_key] = (now, out)
            return out
    except Exception:
        return None


# Įžangos klubas — upstream'ai (klientas gauna per /radio/club, be geo/CORS blokų)
CLUB_RADIO_UPSTREAMS = [
    "https://streams.ilovemusic.de/iloveradio14.mp3",
    "https://play.ilovemusic.de/ilm_ilovepartyhard/",
]


@app.get("/radio/club")
def radio_club_proxy():
    """Same-origin klubinis srautas — veikia visiems (be išorinio stream blokavimo)."""

    def generate():
        last_err = None
        for url in CLUB_RADIO_UPSTREAMS:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "PenktadienioAukcionasRadio/1.0",
                        "Icy-MetaData": "0",
                        "Connection": "keep-alive",
                    },
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    while True:
                        chunk = resp.read(16384)
                        if not chunk:
                            break
                        yield chunk
                return
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"radio upstream fail: {last_err}")

    return StreamingResponse(
        generate(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/desk_songs")
def api_desk_songs():
    """Viešas dainų sąrašas — paspaudimui. Be failo = ok false."""
    items = []
    for n, title in DESK_SONG_TITLES.items():
        items.append({
            "n": n,
            "title": title,
            "ok": desk_song_path(n) is not None,
            "url": f"/desk-songs/{n}",
        })
    items.sort(key=lambda x: x["n"])
    return {"ok": True, "song": desk_song_public(), "items": items}


@app.get("/api/desk_song")
def api_desk_song_now():
    return {"ok": True, "song": desk_song_public()}


@app.post("/api/desk_song/next")
def api_desk_song_next():
    """Dainai pasibaigus — kita (ne ta pati). Synkas visiems per state."""
    if get_desk_song_n() <= 0:
        return {"ok": True, "song": None, "skipped": True}
    n = next_desk_song_n()
    set_desk_song_n(n)
    return {"ok": True, "song": desk_song_public()}


@app.get("/api/dancer")
def api_dancer_now():
    return {"ok": True, "dancer": get_dancer_public()}


@app.post("/api/dancer/next")
async def api_dancer_next():
    """F5 / rankinis „kita šokėja“ — keičia VISIEMS vienu metu (3 s apsauga nuo spam)."""
    return {"ok": True, "dancer": dancer_next_public()}


@app.get("/desk-songs/{n}")
def desk_song_file(n: int):
    if int(n) not in DESK_SONG_TITLES:
        raise HTTPException(404, "nėra tos dainos")
    p = desk_song_path(int(n))
    if not p:
        raise HTTPException(404, "nėra tos dainos")
    return FileResponse(
        p,
        media_type="audio/webm",
        headers={"Cache-Control": "public, max-age=3600", "Accept-Ranges": "bytes"},
    )


@app.post("/api/admin/desk_song")
async def api_admin_desk_song(request: Request):
    """Paspausta daina: nutildo radiją ir groja visiems. n=0 — radijas atgal (F7)."""
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    raw = body.get("n", body.get("song", 0))
    try:
        n = int(raw or 0)
    except (TypeError, ValueError):
        n = 0
    if n and n not in DESK_SONG_TITLES:
        raise HTTPException(400, "nėra tokio numerio")
    if n and not desk_song_path(n):
        raise HTTPException(404, "failas neįkeltas")
    set_desk_song_n(n)
    return {"ok": True, "song": desk_song_public()}


@app.get("/api/radio/now")
def api_radio_now(segment: str = "", stream: str = ""):
    """Dabar grojanti daina — PIRMENYBĖ ICY iš streamo (kas tikrai groja)."""
    segment = (segment or "").strip().lower()[:48]
    stream = (stream or "").strip()[:500]
    # Default: tas pats club stream kaip įžangoje
    if not stream or stream.startswith("/"):
        stream = CLUB_RADIO_UPSTREAMS[0]
    if not segment:
        segment = "ilovepartyhard"
    if stream.startswith("https://"):
        icy = _fetch_icy_now(stream)
        if icy and icy.get("ok") and (icy.get("artist") or icy.get("title")):
            return icy
    if segment:
        ilove = _fetch_ilove_segment(segment)
        if ilove and ilove.get("ok"):
            return ilove
    return {"ok": False, "artist": "", "title": ""}


def _read_muzika_notepad() -> str:
    try:
        if MUZIKA_NOTEPAD_FILE.is_file():
            return MUZIKA_NOTEPAD_FILE.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


@app.get("/api/muzika/notepad")
def api_muzika_notepad():
    """Grąžina visą patinkančių dainų notepad tekstą."""
    return {"ok": True, "text": _read_muzika_notepad(), "file": MUZIKA_NOTEPAD_FILE.name}


@app.get("/api/muzika/download")
def api_muzika_download():
    """Atsisiųsti notepad failą."""
    if not MUZIKA_NOTEPAD_FILE.is_file():
        MUZIKA_NOTEPAD_FILE.write_text("", encoding="utf-8")
    return FileResponse(
        MUZIKA_NOTEPAD_FILE,
        media_type="text/plain; charset=utf-8",
        filename="patinkancios_muzikos_notepad.txt",
    )


@app.post("/api/muzika/save")
async def api_muzika_save(request: Request):
    """Įrašo patinkančią radijo dainą į tekstinį notepad failą."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    artist = (body.get("artist") or "").strip()[:120]
    title = (body.get("title") or "").strip()[:180]
    station = (body.get("station") or "").strip()[:80]
    if not artist and not title:
        raise HTTPException(400, "Dar nežinoma kokia daina groja — palauk kelias sekundes")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    q = f"{artist} {title}".strip()
    line = f"{ts} | GRUPĖ: {artist} | DAINA: {title}"
    if station:
        line += f" | Stotis: {station}"
    line += f" | YouTube: https://www.youtube.com/results?search_query={quote(q)}"
    line += f" | Spotify: https://open.spotify.com/search/{quote(q)}\n"
    try:
        with open(MUZIKA_NOTEPAD_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        raise HTTPException(500, f"Nepavyko įrašyti: {type(e).__name__}")
    return {"ok": True, "text": _read_muzika_notepad(), "line": line.strip()}


@app.get("/api/tts")
def api_tts(text: str = "", fast: int = 0, speed: float = 0.0):
    text = _soft_trim((text or "").strip(), 880)
    if not text:
        raise HTTPException(400, "text privalomas")
    is_fast = bool(fast)
    sp = None
    try:
        if speed and float(speed) > 0:
            sp = float(speed)
    except Exception:
        sp = None
    audio = None
    media = "audio/mpeg"
    src = "none"
    # Tikras VILKAS_8: GPU sample_cache -> lt_vc -> XTTS.
    # Senas ElevenLabs v3/v4 hash kešas sąmoningai nebevartojamas.
    if TTS_PROVIDER in ("vilkas", "local") or VILKAS_LOCAL_TTS_FIRST:
        tts_text = _calm_text(text)
        norm_sp = _norm_speed(is_fast, sp)
        # Ilgesni pristatymai — +12% tada +4% vs ankstesnis 0.86
        if not is_fast and len(tts_text) > 180:
            norm_sp = min(norm_sp, 1.00)
        audio, media = _vilkas_local_synthesize(tts_text, speed=norm_sp)
        if audio:
            src = "vilkas_local"
    # 2) ElevenLabs TIK jei ne LOCAL_ONLY ir provider leidzia
    if not audio and not VILKAS_LOCAL_ONLY and TTS_PROVIDER in ("elevenlabs", "edge", "auto"):
        if TTS_PROVIDER == "edge":
            audio = _edge_synthesize(text, fast=is_fast) or _elevenlabs_synthesize(text, fast=is_fast, speed=sp)
            src = "edge_or_eleven" if audio else src
        else:
            audio = _elevenlabs_synthesize(text, fast=is_fast, speed=sp)
            src = "elevenlabs" if audio else src
    if not audio and TTS_PROVIDER == "edge" and not VILKAS_LOCAL_ONLY:
        audio = _edge_synthesize(text, fast=is_fast)
        src = "edge" if audio else src
    if not audio:
        raise HTTPException(503, "tts_unavailable")
    return Response(
        content=audio,
        media_type=media if media.startswith("audio/") else "audio/mpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Access-Control-Allow-Origin": "*",
            "X-Vilkas-Voice": f"local|{src}|{TTS_AUDIO_VER}",
            "X-Vilkas-TTS-Source": src,
        },
    )


@app.post("/api/vilkas/think")
async def api_vilkas_think(request: Request):
    """Profesionalaus vedejo eilute is RO smegenu (be ElevenLabs)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    event = (body.get("event") or "nudge").strip()
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else body
    url = f"{VILKAS_LOCAL_TTS_URL}/v1/think"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"event": event, "payload": payload or {}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"text": "Nestabdom, judam! Kas kitas?", "mood": "fallback", "error": f"{type(e).__name__}"}


@app.post("/api/register")
async def api_register(request: Request):
    # Tikri žmonės — uždaryta (praktikos režimas). Botai seedinami tik serveryje.
    if not PUBLIC_REGISTRATION_OPEN:
        raise HTTPException(403, PUBLIC_REG_CLOSED_MSG)
    body = await request.json()
    name = (body.get("name") or "").strip()[:80]
    nickname = (body.get("nickname") or "").strip()[:24]  # neprivalomas
    contact = (body.get("contact") or "").strip()[:60]
    phone = _normalize_phone(body.get("phone") or body.get("tel"))
    pay_method = _normalize_pay_method(body.get("pay_method"))
    if not name or not contact:
        raise HTTPException(400, "vardas, el. paštas ir telefonas privalomi")
    if not _looks_like_email(contact):
        raise HTTPException(400, "nurodykite el. paštą — ten gausite mokėjimo instrukcijas")
    preferred = nickname or (name.split()[0] if name.split() else name)
    pid = str(uuid.uuid4())
    now = time.time()
    ip = ""
    try:
        ip = (request.client.host if request.client else "") or ""
        fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if fwd:
            ip = fwd
    except Exception:
        pass
    ua = (request.headers.get("user-agent") or "")[:240]
    con = db()
    # Unikalus viešas vardas aukcione (Jonas → Jonas2 jei Jonas jau yra)
    public_name = _unique_public_nickname(con, preferred)
    nickname = public_name  # visada saugom unikalų — statymai / sąrašas nesimaišo
    con.execute(
        "INSERT INTO participants (pid, name, nickname, contact, phone, pay_method, at) VALUES (?,?,?,?,?,?,?)",
        (pid, name, nickname, contact, phone, pay_method, now),
    )
    con.commit()
    con.close()
    row = {
        "pid": pid,
        "name": name,
        "nickname": nickname,
        "contact": contact,
        "phone": phone,
        "email_domain": _email_domain(contact),
        "pay_method": pay_method,
        "at": now,
        "at_lt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "ip": ip,
        "user_agent": ua,
        "is_demo": False,
    }
    _rebuild_admin_registracijos_files(extra=row)
    return {
        "pid": pid,
        "nickname": nickname,
        "public_name": public_name,
        "pay_method": pay_method,
        "email_domain": row["email_domain"],
        "phone": phone,
    }


@app.post("/api/my_payment")
async def api_my_payment(request: Request):
    """Mokėjimo el. paštas tik laimėtojui (pagal pid) — viešai nerodomas."""
    body = await request.json()
    pid = (body.get("pid") or "").strip()
    if not pid:
        raise HTTPException(400, "pid privalomas")
    con = db()
    p = con.execute("SELECT * FROM participants WHERE pid=?", (pid,)).fetchone()
    if not p:
        con.close()
        raise HTTPException(403, "neregistruotas dalyvis")
    lot = get_active_lot(con)
    lot = maybe_end_lot(con, lot)
    lot_d = dict(lot) if lot else None
    pub_nick = (p["nickname"] or p["name"] or "").strip()
    if not lot_d or lot_d.get("status") != "ended" or (lot_d.get("current_bidder") or "").strip() != pub_nick:
        con.close()
        return {
            "ok": False,
            "winner": False,
            "message": "Mokėjimo instrukcijas gausite el. paštu, jei laimėsite lotą.",
        }
    info = _winner_pay_payload(con, lot_d)
    con.close()
    if not info:
        return {"ok": False, "winner": False, "message": "Laimėtojo duomenų nerasta."}
    return {
        "ok": True,
        "winner": True,
        "pay_label": info["pay_label"],
        "pay_email": info["pay_email"],
        "pay_hint": info["pay_hint"],
        "pay_method": info["pay_method"],
        "lot_title": info["lot_title"],
        "amount": info["amount"],
        "shipping": info["shipping"],
        "total": info["total"],
        "message": "Mokėkite tik savo pasirinkta sistema. Instrukcijos taip pat bus išsiųstos į jūsų el. paštą.",
    }


@app.post("/api/bid")
async def api_bid(request: Request):
    if AUCTION_LOCKED:
        raise HTTPException(403, AUCTION_LOCK_MSG)
    body = await request.json()
    pid = body.get("pid")
    return _place_bid(pid)


def _place_bid(pid):
    """Bendras žmogaus ir demo botų statymo kelias."""
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        p = con.execute("SELECT * FROM participants WHERE pid=?", (pid,)).fetchone()
        if not p:
            raise HTTPException(403, "neregistruotas dalyvis")
        nickname = (p["nickname"] or "").strip() or (p["name"] or "").strip().split()[0] or (p["name"] or "").strip()
        if not nickname:
            raise HTTPException(403, "neregistruotas dalyvis")
        lot = get_active_lot(con)
        lot = maybe_end_lot(con, lot)
        if not lot or lot["status"] != "live":
            raise HTTPException(409, "nera aktyvaus loto")
        if lot["starts_at"] and time.time() < lot["starts_at"]:
            raise HTTPException(409, "lotas dar neprasidejo")
        if lot["current_bidder"] and lot["current_bidder"] == nickname:
            con.rollback()
            return {"ok": True, "current_price": lot["current_price"], "already": True}
        step = step_for(lot["current_price"])
        new_price = round(lot["current_price"] + step, 2)
        now = time.time()
        new_ends = now + COUNTDOWN_S
        con.execute(
            "UPDATE lots SET current_price=?, current_bidder=?, ends_at=? WHERE id=?",
            (new_price, nickname, new_ends, lot["id"]),
        )
        con.execute(
            "INSERT INTO bids (lot_id, name, amount, at) VALUES (?,?,?,?)",
            (lot["id"], nickname, new_price, now),
        )
        bid_txt = _bid_praise_text(nickname, new_price, lot)
        event = emit_event(
            "bid",
            _with_intonacija({
                "lot_id": lot["id"], "name": nickname, "amount": new_price,
                "text": bid_txt.get("text") if isinstance(bid_txt, dict) else bid_txt,
                "phrase_id": (bid_txt or {}).get("phrase_id") if isinstance(bid_txt, dict) else None,
            }, seed=f"bid:{lot['id']}", name=nickname),
            90, 90, f"bid:{lot['id']}:{nickname}:{new_price}:{now}", con=con,
        )
        con.commit()
        return {
            "ok": True, "current_price": new_price,
            "event_id": event["event_id"] if event else None,
        }
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _next_lot_number(con):
    row = con.execute("SELECT COUNT(*) c FROM lots").fetchone()
    return row["c"] + 1


def _save_photo(photo: UploadFile):
    if photo is None or not photo.filename:
        return None
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    photo_file = uuid.uuid4().hex + ext
    with open(PHOTOS_DIR / photo_file, "wb") as f:
        shutil.copyfileobj(photo.file, f)
    return photo_file


def _insert_lot(con, status, title, description, price, shipping, photo_file, queue_order=None,
                pluses="", defects="", included="", condition=""):
    lot_number = _next_lot_number(con)
    now = time.time()
    starts_at = now + STARTUP_COUNTDOWN_S if status == "live" else None
    # Taisyklinga LT ekrane ir Vilko kalboje — net jei įvesta be lietuviškų raidžių
    title = _lt_fix(title or "")
    description = _lt_fix(description or "")
    pluses, defects, included = _lt_fix(pluses or ""), _lt_fix(defects or ""), _lt_fix(included or "")
    con.execute(
        """INSERT INTO lots (lot_number, title, description, photo_file,
           starting_price, current_price, shipping, current_bidder,
           starts_at, ends_at, status, created_at, queue_order, resolved_at,
           pluses, defects, included, condition)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (lot_number, title, description, photo_file, price, price, shipping,
         None, starts_at, (starts_at + COUNTDOWN_S) if starts_at else None, status, now, queue_order, None,
         pluses, defects, included, condition),
    )
    con.commit()
    return lot_number


def publish_next_from_queue(con):
    row = con.execute(
        "SELECT * FROM lots WHERE status='queued' ORDER BY queue_order ASC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    starts_at = time.time() + STARTUP_COUNTDOWN_S
    con.execute(
        "UPDATE lots SET status='live', starts_at=?, ends_at=?, queue_order=NULL WHERE id=?",
        (starts_at, starts_at + COUNTDOWN_S, row["id"]),
    )
    con.commit()
    return dict(con.execute("SELECT * FROM lots WHERE id=?", (row["id"],)).fetchone())


def recycle_unsold_into_queue(con) -> int:
    """Nepaduoti (ended be laimėtojo) grįžta į eilę — ratas (net jei queue jau turi lotų)."""
    row_max = con.execute(
        "SELECT COALESCE(MAX(queue_order), 0) AS m FROM lots WHERE status='queued'"
    ).fetchone()
    max_order = int(row_max["m"] if row_max is not None else 0)
    n = 0
    for row in con.execute(
        "SELECT * FROM lots WHERE status='ended' "
        "AND (current_bidder IS NULL OR current_bidder='') "
        "ORDER BY id ASC"
    ).fetchall():
        max_order += 1
        n += 1
        con.execute(
            "UPDATE lots SET status='queued', queue_order=?, "
            "current_bidder=NULL, starts_at=NULL, ends_at=NULL, "
            "resolved_at=NULL WHERE id=?",
            (max_order, row["id"]),
        )
    if n:
        con.commit()
    return n


def advance_to_next_lot_now(con):
    """Po loto pabaigos — iškart kitas live (be kavos stovėjimo)."""
    if get_live_lot(con):
        return get_live_lot(con)
    recycle_unsold_into_queue(con)
    return publish_next_from_queue(con)



@app.post("/api/admin/add")
async def api_admin_add(
    password: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    price: float = Form(1.0),
    shipping: float = Form(4.0),
    photo: UploadFile = File(None),
    pluses: str = Form(""),
    defects: str = Form(""),
    included: str = Form(""),
    condition: str = Form(""),
):
    if password != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    photo_file = _save_photo(photo)
    extra = dict(pluses=pluses.strip()[:300], defects=defects.strip()[:300],
                 included=included.strip()[:300], condition=condition.strip()[:40])
    con = db()
    active = get_live_lot(con)
    active = maybe_end_lot(con, active)
    # BE F9 viskas keliauja į EILĘ (niekas nestartuoja iki Mindaugo F9)
    if not active and get_vilkas_stage_on():
        lot_number = _insert_lot(con, "live", title.strip(), description.strip(), price, shipping, photo_file, **extra)
        con.close()
        return {"ok": True, "status": "live", "lot_number": lot_number}
    else:
        max_order = con.execute(
            "SELECT COALESCE(MAX(queue_order),0) m FROM lots WHERE status='queued'"
        ).fetchone()["m"]
        lot_number = _insert_lot(con, "queued", title.strip(), description.strip(), price, shipping, photo_file, queue_order=max_order + 1, **extra)
        con.close()
        return {"ok": True, "status": "queued", "lot_number": lot_number}


@app.post("/api/admin/dashboard")
async def api_admin_dashboard(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    con = db()
    lot = get_active_lot(con)
    lot = maybe_end_lot(con, lot)
    queue = get_queue(con)
    past = get_past_lots(con, limit=15, exclude_id=lot["id"] if lot else None)
    lot_out = dict(lot) if lot else None
    winner_pay = _winner_pay_payload(con, lot_out) if lot_out else None
    past_out = []
    for p in past:
        pd = dict(p)
        w = _winner_pay_payload(con, pd)
        if w:
            pd["winner_contact"] = w["winner_contact"]
            pd["pay_method"] = w["pay_method"]
            pd["pay_label"] = w["pay_label"]
            pd["pay_email"] = w["pay_email"]
            pd["pay_total"] = w["total"]
        past_out.append(pd)
    people = _list_registrations(con, include_demo=False)
    domains: dict[str, int] = {}
    for person in people:
        d = person.get("email_domain") or "(nėra)"
        domains[d] = domains.get(d, 0) + 1
    con.close()
    try:
        _rebuild_admin_registracijos_files()
    except Exception:
        pass
    return {
        "ok": True,
        "lot": lot_out,
        "winner_pay": winner_pay,
        "queue": queue,
        "past_lots": past_out,
        "registrations": people,
        "registration_count": len(people),
        "email_domains": [{"domain": k, "count": v} for k, v in sorted(domains.items(), key=lambda x: (-x[1], x[0]))],
    }


@app.post("/api/admin/end_lot")
async def api_admin_end_lot(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    con = db()
    lot = con.execute(
        "SELECT * FROM lots WHERE status='live' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if lot:
        con.execute(
            "UPDATE lots SET status='ended', resolved_at=? WHERE id=?",
            (time.time(), lot["id"]),
        )
        con.commit()
    con.close()
    return {"ok": True}


@app.post("/api/admin/queue/delete")
async def api_admin_queue_delete(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    lot_id = body.get("id")
    con = db()
    row = con.execute("SELECT * FROM lots WHERE id=? AND status='queued'", (lot_id,)).fetchone()
    if row:
        if row["photo_file"]:
            (PHOTOS_DIR / row["photo_file"]).unlink(missing_ok=True)
        con.execute("DELETE FROM lots WHERE id=?", (lot_id,))
        con.commit()
    con.close()
    return {"ok": True}


@app.post("/api/admin/queue/move")
async def api_admin_queue_move(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    lot_id = body.get("id")
    direction = body.get("dir")
    con = db()
    queue = get_queue(con)
    ids = [r["id"] for r in queue]
    if lot_id in ids:
        idx = ids.index(lot_id)
        swap_idx = idx - 1 if direction == "up" else idx + 1
        if 0 <= swap_idx < len(queue):
            a, b = queue[idx], queue[swap_idx]
            con.execute("UPDATE lots SET queue_order=? WHERE id=?", (b["queue_order"], a["id"]))
            con.execute("UPDATE lots SET queue_order=? WHERE id=?", (a["queue_order"], b["id"]))
            con.commit()
    con.close()
    return {"ok": True}


@app.post("/api/admin/vilkas_stage")
async def api_admin_vilkas_stage(request: Request):
    """Mindaugo mygtukas: įjungti / išjungti Vilką scenoje (visi klientai sinchronizuojasi)."""
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    on = bool(body.get("on"))
    if not on:
        set_vilkas_stage_on(False)
        return {"ok": True, "vilkas_stage_on": False}
    # Welcome TIK per director_tick (unique_key welcome:diena) — čia NEEMITINTI (dubliuodavo balsą)
    if not AUCTION_LOCKED:
        # F9 ON: laikmatis STARTUOJA DABAR (ne anksčiau).
        # Jei live tuščias — priverstinai skelbiam pirmą iš eilės.
        # Jei live yra (laukė sušaldytas) — atnaujinam laikmatį nuo dabar,
        # kad lotas akimirksniu nesibaigtų (be statymų) arba nepratęstų seno.
        try:
            con = db()
            try:
                # NEPARDUOTI (ended be laimėtojo) — atgal į EILĘ, sukasi ratu.
                # Parduoti (su laimėtoju) lieka ended.
                max_order = con.execute(
                    "SELECT COALESCE(MAX(queue_order),0) m FROM lots WHERE status='queued'"
                ).fetchone()["m"]
                for row in con.execute(
                    "SELECT * FROM lots WHERE status='ended' "
                    "AND (current_bidder IS NULL OR current_bidder='') "
                    "ORDER BY id ASC"
                ).fetchall():
                    max_order += 1
                    con.execute(
                        "UPDATE lots SET status='queued', queue_order=?, "
                        "current_bidder=NULL, starts_at=NULL, ends_at=NULL, "
                        "resolved_at=NULL WHERE id=?",
                        (max_order, row["id"]),
                    )
                con.commit()
                live = get_live_lot(con)
                if not live and get_queue(con):
                    publish_next_from_queue(con)
                elif live:
                    nb = con.execute(
                        "SELECT COUNT(*) c FROM bids WHERE lot_id=?", (live["id"],)
                    ).fetchone()["c"]
                    now = time.time()
                    if not nb:
                        starts_at = now + OPENING_COFFEE_S
                        con.execute(
                            "UPDATE lots SET starts_at=?, ends_at=? WHERE id=?",
                            (starts_at, starts_at + COUNTDOWN_S, live["id"]),
                        )
                    else:
                        con.execute(
                            "UPDATE lots SET ends_at=? WHERE id=?",
                            (now + COUNTDOWN_S, live["id"]),
                        )
                    con.commit()
                # F9: senų scenos raktų trynimas — antras įjungimas / ratas vėl kalba
                live2 = get_live_lot(con)
                if live2:
                    sa = int(float(live2.get("starts_at") or 0))
                    lid = int(live2["id"])
                    day = time.strftime("%Y-%m-%d", time.localtime())
                    for uk in (
                        f"welcome:{day}",
                        f"lot_intro:{lid}:{sa}",
                        f"start:{lid}:{sa}",
                        f"nudge:{lid}:{sa}",
                        f"phone:{lid}:{sa}",
                        f"phone:{lid}:{sa}:2",
                        f"phone:{lid}:{sa}:3",
                        f"joke:{lid}:{sa}",
                        f"joke_pre:{lid}:{sa}",
                        f"guitar:{lid}:{sa}",
                    ):
                        try:
                            con.execute("DELETE FROM events WHERE unique_key=?", (uk,))
                        except Exception:
                            pass
                    con.commit()
            finally:
                con.close()
        except Exception as e:
            print(f"[vilkas_stage] force publish fail: {e}", flush=True)
            raise HTTPException(500, "nepavyko paruošti Vilko scenos") from e
    set_vilkas_stage_on(True)
    try:
        director_tick()
    except Exception as e:
        set_vilkas_stage_on(False)
        print(f"[vilkas_stage] director after F9 fail: {e}", flush=True)
        raise HTTPException(500, "nepavyko paleisti Vilko režisieriaus") from e
    return {"ok": True, "vilkas_stage_on": get_vilkas_stage_on()}


@app.post("/api/admin/vilkas_phone")
async def api_admin_vilkas_phone(request: Request):
    """F11: Mindaugas paleidžia vieną iš 3 klasikinių telefono atsiliepimų (ciklas 1→2→3→1)."""
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    core = list(VILKAS8_PHONE_CORE)
    if not core:
        raise HTTPException(500, "nera telefono fraziu")
    raw_n = body.get("n")
    if raw_n is None or raw_n == "" or str(raw_n).lower() == "next":
        idx = int(_phone_manual_n.get("n") or 0) % len(core)
        _phone_manual_n["n"] = (idx + 1) % len(core)
    else:
        try:
            idx = max(0, min(len(core) - 1, int(raw_n) - 1))
        except Exception:
            idx = 0
        _phone_manual_n["n"] = (idx + 1) % len(core)
    text = core[idx]
    n = idx + 1
    lot_id = None
    try:
        con = db()
        try:
            lot = get_live_lot(con) or get_active_lot(con)
            if lot:
                lot_id = lot["id"]
        finally:
            con.close()
    except Exception:
        pass
    uk = f"phone_manual:{time.time_ns()}:{n}"
    emit_event(
        "phone",
        {"lot_id": lot_id, "n": n, "text": text, "phrase_id": None, "manual": True},
        95,
        45,
        uk,
    )
    return {
        "ok": True,
        "n": n,
        "text": text,
        "next_n": int(_phone_manual_n.get("n") or 0) + 1,
        "core_count": len(core),
    }


@app.post("/api/admin/reset")
async def api_admin_reset(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    con = db()
    for row in con.execute("SELECT photo_file FROM lots WHERE photo_file IS NOT NULL"):
        (PHOTOS_DIR / row["photo_file"]).unlink(missing_ok=True)
    con.executescript("DELETE FROM bids; DELETE FROM lots; DELETE FROM participants;")
    con.commit()
    con.close()
    return {"ok": True}


# ---------- automatinis eiles stumdymas ----------

def _lot_intro_text(lot):
    """TRUMPAS pristatymas (nuoseklus startas) — be ilgo aprašymo."""
    cond_map = {"kaip_nauja": "kaip nauja", "labai_gera": "labai gera", "naudota": "naudota", "gera": "gera"}
    parts = [
        f"Lotas numeris {lot.get('lot_number')}.",
        f"{_lt_fix(lot.get('title') or 'Prekė')}.",
        f"Pradinė kaina {_lt_eur(lot.get('starting_price') or lot.get('current_price') or 0)}.",
    ]
    cond = (lot.get("condition") or "").strip()
    if cond:
        parts.append(f"Būklė {cond_map.get(cond, cond.replace('_', ' '))}.")
    parts.append("Ruoškitės kelti kainą vienu euru.")
    return _calm_text(" ".join(parts))


# 3 klasikinės frazės — F11 ciklina jas (Mindaugas klaviatūra)
VILKAS8_PHONE_CORE = [
    "Alio, alio! Aš darbe — Penktadienio aukcione! Prekyba, prekyba užsiimu!",
    "Alio, alio! Gerai — aš perskambinsiu, netrukdyk!",
    "Alio! Dabar negaliu ilgai kalbėti — Vilkas veda aukcioną. Perskambinsiu!",
]
# Papildomos (automatinė praktika / mokykla) — įvairovė, kad neįkyrėtų
VILKAS8_PHONE_EXTRA = [
    "Aliooo Antanai! Ne dabar — aš scenoje, kainą kelia pirkėjai!",
    "Aliooo Jonai! Palauk penkias minutes — Vilkas dar nebaigė loto!",
    "Alio, Birute! Taip, girdžiu, bet dabar aukcionas — vėliau kavą!",
    "Aliooo, šefe! Ne, dar nepralaimėjau — aš vedu, ne perku!",
    "Alio? Kazimierai! Aš ne taksi, aš Vilkas — keliam eurus!",
    "Alio, mama! Taip, valgiau. Ne, dar nenupirkau — kiti kelia!",
    "Alio, girdžiu! Taip, prekės čia geros, bet dabar manęs laukia pirkėjai!",
    "Alio, šefe! Taip, dirbu — Vilkas parduoda, pirkėjai spaudžia!",
    "Aliooo Onute! Palauk — dabar bajeriukas, paskui tau paskambinsiu!",
]
VILKAS8_PHONE = VILKAS8_PHONE_CORE + VILKAS8_PHONE_EXTRA
_phone_manual_n = {"n": 0}  # 0..2 ciklas F11
VILKAS8_JOKES = [
    "Bajeriukas: kas nespėjo — tas pavydės iki sekmadienio!",
    "Na taip — piniginė plonesnė, o šypsena platesnė!",
    "Kaip sako Vilkas: kas drįso — tas ir turi!",
    "Ir vėl — vienas laimingas, visi kiti — su istorija papasakoti!",
]
VILKAS8_COFFEE = [
    "Trumpa kavos pertraukėlė! Opa opa — Vilkas atsikvėpia…",
    "Kava karšta, o lotai — dar karštesni! Opa!",
    "Gurkšnelis kavos — ir vėl į sceną. Opa opa!",
]
VILKAS8_SING = [
    "La-la-la — {daina}! Opa opa, Vilkas padainuoja su muzika!",
    "O-pa o-pa — {daina}, {daina}! Ir vėl į prekybą!",
    "Hmm-hmm — girdžiu bitą: {daina}! Opa opaapa!",
    "Na taip — groja {daina}, Vilkas pritaria: la la, kelkit kainą!",
    "Trumpas refrenas: {daina} — eurų lietus!",
]


# === VILKO_MOKYKLA_SERVER_START (Fable 2026-10-08) ===
import random as _vk_random
from collections import deque
VILKO_BRAIN_PATH = Path(os.environ.get("VILKO_SMEGENYS", str(BASE_DIR / "vilko_mokykla" / "smegenys.json")))
_vilko_brain_cache = {"mtime": 0.0, "data": None}


def vilko_brain():
    """smegenys.json — hot reload pagal mtime (mokykla rašo, app.py skaito; be restart)."""
    try:
        st = VILKO_BRAIN_PATH.stat()
        if _vilko_brain_cache["data"] is None or st.st_mtime != _vilko_brain_cache["mtime"]:
            with open(VILKO_BRAIN_PATH, encoding="utf-8") as f:
                _vilko_brain_cache["data"] = json.load(f)
            _vilko_brain_cache["mtime"] = st.st_mtime
    except Exception:
        pass
    return _vilko_brain_cache["data"] or {}


_VP_RECENT = {}  # kind -> deque(maxlen=8) paskutiniu pasirinktu fraziu id (kad nesikartotu)
_VP_LAST = {}    # kind -> paskutinis pasirinktas fraziu id (kad nebutu dvieju is eiles vienodu)


def _vp(kind, seed, fallback_list):
    """Frazes parinkimas: 0.55*kokybe(a/(a+b)) + 0.35*atsitiktinumas + 0.10*naujumas.
    To paties kind frazes nesikartoja: paskutines 8 laikomos atmintyje,
    dvieju is eiles vienodu nebus. Grazina payload dali {"text","phrase_id"}."""
    try:
        arr = [p for p in (vilko_brain().get("frazes") or {}).get(kind, []) if p.get("aktyvi", True) and p.get("tekstas")]
    except Exception:
        arr = []
    if not arr:
        fl = list(fallback_list or [""])
        return {"text": fl[int(seed) % len(fl)], "phrase_id": None}
    recent = _VP_RECENT.setdefault(kind, deque(maxlen=8))
    pool = [p for p in arr if str(p.get("id")) not in recent]
    if not pool:
        pool = list(arr)
    last = _VP_LAST.get(kind)
    if len(pool) > 1 and last is not None:
        pool = [p for p in pool if str(p.get("id")) != str(last)] or pool
    rnd = _vk_random.Random(f"{kind}:{seed}:{time.time_ns()}")
    best, bv = None, -1.0
    for p in pool:
        a = max(0.01, float(p.get("a", 1)))
        b = max(0.01, float(p.get("b", 1)))
        try:
            kartai = float(p.get("kartai") or 0)
        except Exception:
            kartai = 0.0
        score = 0.55 * (a / (a + b)) + 0.35 * rnd.random() + 0.10 * (1.0 / (1.0 + kartai / 30.0))
        if score > bv:
            best, bv = p, score
    chosen = str(best.get("id"))
    recent.append(chosen)
    _VP_LAST[kind] = chosen
    return {"text": best["tekstas"], "phrase_id": best.get("id")}


def _sing_hook() -> str:
    """Trumpas grojančios dainos „kabliukas“ — ją Vilkas ir užtraukia.
    „Britney Spears — Toxic“ → „Toxic“."""
    try:
        song = desk_song_public()
    except Exception:
        song = None
    if not song:
        return ""
    title = str(song.get("title") or "").strip()
    if not title:
        return ""
    # po brūkšnio — pats dainos pavadinimas (be atlikėjo)
    for dash in ("—", "–", " - "):
        if dash in title:
            title = title.split(dash, 1)[1]
            break
    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" .,!?-–—")
    if not title:
        return ""
    # pavadinimai trumpi — kerpam tik jei tikrai ilgas, kad nenukąstų frazės vidury
    if len(title) > 34:
        title = " ".join(title.split()[:4])
    return title


def _vp_sing(seed):
    """Dainavimas kartu: frazę renka mokykla (kategorija 'sing'),
    o {daina} užpildo tuo, kas TIKRAI groja dabar."""
    part = _vp("sing", seed, VILKAS8_SING)
    hook = _sing_hook()
    part["text"] = str(part.get("text") or "").replace("{daina}", hook or "la-la-la")
    if hook:
        part["daina"] = hook
    return part


def _is_female_name(name: str) -> bool:
    """VISI moterų vardai (Agnė, Onutė, Rasa, Greta, Ieva…) — ne tik keli pavyzdžiai.
    Vyrai (Jonas, Tomas, Kajus…) → False."""
    w = (name or "").strip().split()[0].lower() if (name or "").strip() else ""
    if not w:
        return False
    # vyrų galūnės
    if re.search(r"(as|is|ys|us|ius|jus)$", w):
        return False
    # moterų galūnės — bet kuris LT moteriškas vardas
    return bool(re.search(r"(a|ė|e|ia|ija)$", w))


def _pick_intonacija(seed="live", *, force_sexy: bool = False, allow_sexy: bool = False):
    """
    Thompson intonacija.
    Subtilus seksualus profilis galimas ir bendram Vilko vedimui;
    tekstinės pauzės paliekamos tik konkrečiam moters vardo pagyrimui.
    """
    sexy_fb = {
        "intonacija_id": "int-sexy",
        "intonacija": "seksuali",
        "speed": 0.93,
        "soft_pause": True,
        "stability": 0.38,
        "style": 0.42,
    }
    warm_fb = {
        "intonacija_id": "int-warm",
        "intonacija": "šilta",
        "speed": 0.97,
        "soft_pause": False,
        "stability": 0.55,
        "style": 0.20,
    }
    if force_sexy:
        try:
            for p in ((vilko_brain().get("intonacija") or {}).get("profiliai") or []):
                if isinstance(p, dict) and p.get("id") == "int-sexy":
                    return {
                        "intonacija_id": "int-sexy",
                        "intonacija": p.get("pavadinimas") or "seksuali",
                        "speed": float(p.get("speed") or 0.88),
                        "soft_pause": True,
                        "stability": float(p.get("stability") or 0.38),
                        "style": float(p.get("style") or 0.42),
                    }
        except Exception:
            pass
        return sexy_fb
    try:
        arr = [
            p for p in ((vilko_brain().get("intonacija") or {}).get("profiliai") or [])
            if isinstance(p, dict) and p.get("aktyvi", True) and p.get("id")
        ]
    except Exception:
        arr = []
    # Sexy profilis įtraukiamas tik kalbos keliuose, kurie jį aiškiai leidžia.
    if not allow_sexy:
        arr = [p for p in arr if str(p.get("id")) != "int-sexy" and str(p.get("pavadinimas") or "") != "seksuali"]
    if not arr:
        return warm_fb
    rnd = _vk_random.Random(f"inton:{seed}:{int(time.time() // 600)}")
    best, bv = None, -1.0
    for p in arr:
        v = rnd.betavariate(max(0.01, float(p.get("a", 1))), max(0.01, float(p.get("b", 1))))
        if v > bv:
            best, bv = p, v
    return {
        "intonacija_id": best.get("id"),
        "intonacija": best.get("pavadinimas") or best.get("id"),
        "speed": float(best.get("speed") or 1.0),
        "soft_pause": bool(best.get("soft_pause")) if allow_sexy else False,
        "stability": float(best.get("stability") or 0.55),
        "style": float(best.get("style") or 0.2),
    }


def _apply_soft_pause_text(text: str) -> str:
    """Seksualiai — daugiau pauzių (TIK kai sakomas moters vardas)."""
    t = (text or "").strip()
    if not t:
        return t
    t = t.replace("—", "… ").replace(" – ", "… ")
    t = re.sub(r"([,!?])\s*", r"\1 … ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _with_intonacija(payload: dict, seed="live", *, name: str | None = None) -> dict:
    """
    Intonacija į event; subtilus sexy profilis galimas visam vedimui.
    """
    out = dict(payload or {})
    who = name if name is not None else out.get("name")
    female = _is_female_name(str(who or ""))
    ito = _pick_intonacija(seed, force_sexy=female, allow_sexy=True)
    out.update({
        "intonacija_id": ito.get("intonacija_id"),
        "intonacija": ito.get("intonacija"),
        "speed": round(float(ito.get("speed") or 1.0), 3),
        "female_name": bool(female),
    })
    # soft pause tekstui — tik sexy + moters vardas
    if female and ito.get("soft_pause") and out.get("text"):
        out["text"] = _apply_soft_pause_text(str(out["text"]))
    return out


def _bid_praise_text(nickname, price, lot=None):
    """Pagyrimas keliančiam — Onutė pakėlė / šaunuolė stilius. {vardas}{kaina}{preke}."""
    name = (nickname or "drauge").strip().split()[0] or "drauge"
    female = _is_female_name(name)
    praise = "šaunuolė, šaunuolė" if female else "šaunuolis, šaunuolis"
    title = ""
    try:
        title = str((lot or {}).get("title") or "")
    except Exception:
        title = ""
    item = "telefono"
    tl = title.lower()
    if "iphone" in tl or "apple" in tl:
        item = "iPhone"
    elif "samsung" in tl or "galaxy" in tl:
        item = "Samsung"
    elif "nokia" in tl:
        item = "Nokia"
    elif "motorola" in tl or "moto" in tl:
        item = "Motorola"
    price_s = f"{int(round(float(price) or 0))} eurų"
    fb = [
        f"O {name} pakėlė — {praise}! Nori {item}? Viso jau {price_s}. Kas kitas?",
        f"Žiūrėkit — {name} kelia! {praise}! Nori {item}? Dabar {price_s}. Kas atsakys?",
        f"Ooo, {name}! {praise}! Pakėlė kainą — nori {item}? Jau {price_s}. Kas perims?",
        f"Nu va — {name} pakėlė! Brawo! Nori {item}? Kaina {price_s}. Nestabdom!",
        f"Štai {name} spaudžia! {praise}! Gal tikrai nori {item}? {price_s}. Kas kitas?",
    ]
    picked = _vp("bid", f"{name}:{price_s}", fb)
    txt = str(picked.get("text") or fb[0])
    txt = (
        txt.replace("{vardas}", name)
        .replace("{name}", name)
        .replace("{kaina}", price_s)
        .replace("{price}", price_s)
        .replace("{preke}", item)
        .replace("{item}", item)
    )
    # jei smegenų frazė be vardo — įterpti
    if name.lower() not in txt.lower() and "{vardas}" not in (picked.get("text") or ""):
        txt = f"O {name}! " + txt
    # vyrų frazėse neturi likti „šaunuolė“ ir atvirkščiai
    if female:
        txt = txt.replace("šaunuolis, šaunuolis", "šaunuolė, šaunuolė").replace("Šaunuolis", "Šaunuolė")
    else:
        txt = txt.replace("šaunuolė, šaunuolė", "šaunuolis, šaunuolis").replace("Šaunuolė", "Šaunuolis")
    return {"text": txt, "phrase_id": picked.get("phrase_id"), "female_name": female}


def _vp_intro(lot):
    """Loto pristatymas; paskutinis sakinys — išmoktas closer (closer_id į payload)."""
    text = _lot_intro_text(lot)
    out = {"text": text, "closer_id": None}
    try:
        c = _vp("intro_closer", int(lot.get("id") or 0), ["Ruoškitės kelti kainą vienu euru."])
        if c.get("phrase_id") and text.rstrip().endswith("Ruoškitės kelti kainą vienu euru."):
            out["text"] = text.rstrip()[: -len("Ruoškitės kelti kainą vienu euru.")] + c["text"]
            out["closer_id"] = c["phrase_id"]
    except Exception:
        pass
    return out


def _vilko_norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def vilko_answer(q):
    qn = _vilko_norm(q)
    best, best_s = None, 0.0
    for a in vilko_brain().get("atsakymai", []) or []:
        s = 0.0
        for k in a.get("raktai", []):
            kn = _vilko_norm(k)
            if kn and kn in qn:
                s += 1.0 + len(kn) / 20.0
        s *= float(a.get("svoris", 1.0))
        if s > best_s:
            best, best_s = a, s
    return best, best_s


def _vilko_tables(con):
    con.execute("""CREATE TABLE IF NOT EXISTS vilkas_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL NOT NULL, kind TEXT NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}')""")
    con.execute("""CREATE TABLE IF NOT EXISTS vilkas_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL NOT NULL, question TEXT NOT NULL,
        answer_id TEXT, score REAL)""")


@app.get("/api/vilkas/brain")
def api_vilkas_brain():
    b = vilko_brain()
    return {"ok": True, "versija": b.get("versija"), "atnaujinta": b.get("atnaujinta"), "diena": b.get("diena"),
            "judesiai": b.get("judesiai") or {},
            "intonacija": b.get("intonacija") or {}}


@app.post("/api/vilkas/feedback")
async def api_vilkas_feedback(request: Request):
    try:
        d = await request.json()
    except Exception:
        return {"ok": False}
    kind = str((d or {}).get("kind") or "")[:32]
    if kind not in ("motion", "gesture", "speech"):
        return {"ok": False}
    payload = json.dumps((d or {}).get("payload") or {}, ensure_ascii=False)[:4000]
    con = db()
    try:
        _vilko_tables(con)
        con.execute("INSERT INTO vilkas_feedback(created_at,kind,payload) VALUES(?,?,?)", (time.time(), kind, payload))
        con.execute("DELETE FROM vilkas_feedback WHERE id < (SELECT COALESCE(MAX(id),0) FROM vilkas_feedback) - 200000")
        con.commit()
    finally:
        con.close()
    return {"ok": True}


@app.get("/api/vilkas/ask")
def api_vilkas_ask(q: str = ""):
    q = (q or "").strip()[:300]
    if not q:
        return {"ok": False}
    a, s = vilko_answer(q)
    con = db()
    try:
        _vilko_tables(con)
        con.execute("INSERT INTO vilkas_questions(created_at,question,answer_id,score) VALUES(?,?,?,?)",
                    (time.time(), q, a["id"] if a else None, float(s)))
        con.commit()
    finally:
        con.close()
    if a and s >= 1.0:
        return {"ok": True, "atsakymas": a["atsakymas"], "id": a["id"], "balas": s}
    return {"ok": True, "atsakymas": "Gerą klausimą uždavėt — Vilkas pasidomės ir atsakys. O kol kas — kelkit kainą!", "id": None, "balas": s}
# === VILKO_MOKYKLA_SERVER_END ===

def director_tick():
    """Serverio režisierius: vienoda scena visiems prisijungusiems klientams."""
    if not get_vilkas_stage_on():
        return
    con = db()
    try:
        lot = get_active_lot(con)
        lot = maybe_end_lot(con, lot)
        now = time.time()
        day = time.strftime("%Y-%m-%d", time.localtime(now))
        # Dalyvių skaičius welcome frazei
        try:
            n_real = con.execute(
                "SELECT COUNT(*) c FROM participants "
                "WHERE contact IS NULL OR (contact!='' AND contact!='demo')"
            ).fetchone()["c"]
        except Exception:
            n_real = 0
        n_all = con.execute("SELECT COUNT(*) c FROM participants").fetchone()["c"]
        n_see = int(n_real or n_all or 0)
        if n_see <= 0:
            count_lt = "jau kelis dalyvius"
        elif n_see == 1:
            count_lt = "vieną dalyvį"
        elif n_see < 10:
            count_lt = f"{n_see} dalyvius"
        else:
            count_lt = f"{n_see} dalyvių"
        welcome_txt = (
            f"Labas vakaras, susirinkę aukciono dalyviai! "
            f"Šį vakarą aš jus matau — {count_lt}. "
            f"Po trumpos kavos pertraukėlės pradėsime. "
            f"Trumpai apie taisykles: dešiniajame krašte pasiskaitykite. "
            f"O aš tuo tarpu gurkštelėsiu kavos."
        )
        emit_event(
            "welcome",
            {
                "text": welcome_txt,
                "pose": "welcome",
                "coffee_s": OPENING_COFFEE_S,
            },
            55, 900, f"welcome:{day}", con=con,
        )
        if not lot:
            # Eilė / recycle — be live: keliam kitą (ne return be intro).
            if not AUCTION_LOCKED:
                try:
                    nxt = advance_to_next_lot_now(con)
                    if nxt:
                        lot = dict(nxt)
                except Exception as e:
                    print(f"[director] force publish fail: {e}", flush=True)
            con.commit()
            if not lot:
                return
        lot = dict(lot)
        if lot.get("status") != "live":
            # Malonės UI (ended grace) — vis tiek publish_next + intro live lotui.
            if not AUCTION_LOCKED:
                try:
                    nxt = advance_to_next_lot_now(con)
                    if nxt:
                        lot = dict(nxt)
                except Exception as e:
                    print(f"[director] advance after ended fail: {e}", flush=True)
            if lot.get("status") != "live":
                # Dar kartą per live (gal jau kelia maybe_end) — ne return be intro.
                live2 = get_live_lot(con)
                if live2:
                    lot = dict(live2)
                else:
                    con.commit()
                    return
        if lot["status"] == "live":
            _sa = int(float(lot.get("starts_at") or 0))
            _lid = int(lot["id"])
            to_start = float(lot.get("starts_at") or 0) - now
            # Nuoseklus startas: kol kavos pauzė (to_start > 25) — JOKIO lot_intro / bajerių.
            if lot.get("starts_at") and to_start > 25:
                con.commit()
                return
            intro_uk = f"lot_intro:{lot['id']}:{int(float(lot.get('starts_at') or 0))}"
            intro_ttl = max(120, OPENING_COFFEE_S + 60)
            intro_payload = {
                "lot_id": lot["id"], "lot_number": lot.get("lot_number"),
                "title": lot.get("title") or "", **_vp_intro(lot),
                "starts_at": lot.get("starts_at"),
            }
            emit_event(
                "lot_intro",
                intro_payload,
                70, intro_ttl, intro_uk, con=con,
            )
            if lot.get("starts_at") and now >= lot["starts_at"]:
                emit_event(
                    "start",
                    {
                        "lot_id": lot["id"],
                        **_vp("start", _lid, ["Pradedame! Minutė prasideda — spauskite KELTI mygtuką! Kas pirmas?"]),
                    },
                    95, 75, f"start:{lot['id']}:{_sa}", con=con,
                )
                last_bid = con.execute(
                    "SELECT id,at FROM bids WHERE lot_id=? ORDER BY id DESC LIMIT 1", (lot["id"],)
                ).fetchone()
                anchor = float(last_bid["at"]) if last_bid else float(lot["starts_at"])
                bid_key = int(last_bid["id"]) if last_bid else 0
                quiet = now - anchor
                remain = float(lot.get("ends_at") or now) - now
                # Praktika: botai kelia dažnai → „quiet“ niekada neauga → bajeriai/telefonai dingsta.
                # Todėl PRACTICE_BOTS naudoja laiką nuo loto starto (elapsed), ne tik tylą.
                elapsed = now - float(lot.get("starts_at") or now)
                use_elapsed = bool(PRACTICE_BOTS)
                if quiet >= 8 and remain > 12:
                    emit_event(
                        "nudge",
                        {
                            "lot_id": lot["id"],
                            **_vp("nudge", _lid + bid_key, ["Kas kitas? Dar vienas euras ir galite būti priekyje."]),
                        },
                        40, 35, f"nudge:{lot['id']}:{_sa}", con=con,
                    )
                # Trumpas dainavimas su muzika (apsimokymui) — kai tyliau / pagal laiką
                if use_elapsed and elapsed >= 26 and remain > 12:
                    emit_event(
                        "sing",
                        {
                            "lot_id": _lid,
                            **_vp_sing(_lid + 5),
                        },
                        33, 28, f"sing:{_lid}:{_sa}", con=con,
                    )
                elif (not use_elapsed) and quiet >= 24 and remain > 12:
                    emit_event(
                        "sing",
                        {
                            "lot_id": _lid,
                            **_vp_sing(_lid + 5),
                        },
                        33, 28, f"sing:{_lid}:{_sa}", con=con,
                    )
                # 3 skambučiai / ratą — KIEKVIENAS kitas seed (nesikartoja), mokykla renkasi geriausias
                phone_lines = list(VILKAS8_PHONE)
                for n, need in ((1, 14), (2, 34), (3, 46)):
                    need_use = (12 + (n - 1) * 18) if use_elapsed else need
                    gate = elapsed if use_elapsed else quiet
                    if gate >= need_use and remain > 8:
                        # seed keičiasi kas ~2 min + pagal n → frazės sukasi, neįkyri tos pačios
                        phone_seed = int(lot["id"]) * 31 + n * 97 + int(now // 120)
                        emit_event(
                            "phone",
                            {
                                "lot_id": lot["id"], "n": n,
                                **_vp("phone", phone_seed, phone_lines),
                            },
                            35, 30,
                            f"phone:{lot['id']}:{_sa}" + ("" if n == 1 else f":{n}"),
                            con=con,
                        )
                joke_gate = elapsed if use_elapsed else quiet
                if joke_gate >= (22 if use_elapsed else 28) and remain > 8:
                    jokes = VILKAS8_JOKES + [
                        "Bajeriukas: kas nespėjo paspausti, tas rytoj pasakos, kad internetas buvo kaltas!",
                        "Piniginė sako ramiai, o širdis sako — dar vieną eurą!",
                        "Vilkas skaičiuoja ne avis, o jūsų paskutines sekundes!",
                    ]
                    emit_event(
                        "joke",
                        {
                            "lot_id": lot["id"],
                            **_vp("joke", _lid + bid_key + 2, jokes),
                        },
                        38, 35, f"joke:{lot['id']}:{_sa}", con=con,
                    )
        con.commit()
    finally:
        con.close()


def queue_watcher_loop():
    while True:
        try:
            # Ruošimas / užraktas — eilės NENARIAME į live (prekės lieka navigacijoje)
            if AUCTION_LOCKED:
                time.sleep(2)
                continue
            con = db()
            if not get_vilkas_stage_on():
                # BE F9 — eilė nejuda: niekas nesikelia į live, niekas nesibaigia
                con.close()
                time.sleep(2)
                continue
            # maybe_end baigia live + iškart kelia kitą. Malonės UI (get_active_lot)
            # nebeturi blokuoti publish — kitaip Vilkas stovi 8s+ kavą.
            live = get_live_lot(con)
            live = maybe_end_lot(con, live)
            if not get_live_lot(con):
                advance_to_next_lot_now(con)
            con.close()
            director_tick()
        except Exception as e:
            print(f"[director] {type(e).__name__}: {e}", flush=True)
        time.sleep(2)


if BACKGROUND_LOOPS_ENABLED:
    threading.Thread(target=queue_watcher_loop, daemon=True).start()


# ---------- DEMO: 50 dalyvių kova su Vilku (paleidžiama tik per /demo?k=...) ----------

DEMO_KEY = (os.environ.get("DEMO_KEY") or "").strip()
# Žmogus žaidžia kartu su botais — lėtesni statymai, laukiama kol gali spausti
DEMO_HUMAN = (os.environ.get("DEMO_HUMAN") or "1").strip().lower() in ("1", "true", "yes", "on")
# Maratono dalyviai kelia paeiliui; naršyklė nutraukia seną TTS, todėl balsai nesidubliuoja.
# Apsaugotas /demo?k=... režimas visada imituoja tikrus pirkėjus.
DEMO_BOTS = True
DEMO_NAMES_F = ["Rasa", "Angelė", "Greta", "Ieva", "Eglė", "Aistė", "Rūta", "Jurgita", "Laura", "Monika",
                "Gintarė", "Kristina", "Vaida", "Inga", "Asta", "Lina", "Neringa", "Simona", "Dovilė", "Agnė",
                "Justina", "Milda", "Ugnė", "Viktorija", "Jolanta", "Vanessa", "Oksana"]
DEMO_NAMES_M = ["Artūras", "Tomas", "Mantas", "Jonas", "Darius", "Paulius", "Marius", "Lukas", "Andrius", "Vytautas",
                "Rokas", "Giedrius", "Saulius", "Egidijus", "Kęstutis", "Algirdas", "Gintaras", "Tadas", "Simonas", "Karolis",
                "Evaldas", "Žydrūnas", "Povilas", "Deividas", "Aurimas"]
DEMO_LOTS = [
    ("Samsung Galaxy S20 128GB", 30, "demo_samsung_s20.jpg", "gera",
     "128GB atmintis; 120Hz ekranas; baterija 88%; trigubas fotoaparatas", "mažas įbrėžimas ekrano kampe", "USB-C laidas; dėklas", "hot"),
    ("Samsung Galaxy S9 64GB", 20, "demo_s9.jpg", "gera",
     "lenktas AMOLED ekranas; belaidis krovimas; ausinių lizdas", "nusidėvėję rėmelio kampai", "kroviklis", "coffee_f"),
    ("Samsung Galaxy S8 64GB", 15, "demo_s8.jpg", "naudota",
     "begalinis ekranas; atsparus vandeniui; atrakina veidu", "baterija 79%", "USB-C laidas", "duel"),
    ("Samsung Galaxy S7 32GB", 10, "demo_s7.jpg", "naudota",
     "legendinis fotoaparatas; atminties kortelės lizdas; tvirtas", "nubrozdinta nugarėlė", "", "coffee_m"),
    ("Samsung Galaxy S6 32GB", 6, "demo_s6.jpg", "naudota",
     "metalinis korpusas; greitas krovimas; puikus pirmam telefonui", "plonas įbrėžimas ekrane", "kroviklis", "hot"),
    ("Motorola Moto G 64GB", 8, "demo_motorola.jpg", "gera",
     "didelė baterija; švarus Android; dvi SIM kortelės", "smulkūs įbrėžimai nugarėlėje", "dėklas", "last_second"),
    ("Apple iPhone XS 64GB auksinis", 60, "demo_iphone_xs.jpg", "gera",
     "Face ID; OLED ekranas; dviguba kamera; auksinė spalva", "baterija 81%", "originali dėžutė; laidas", "duel"),
    ("Nokia Lumia 925 16GB", 12, "demo_lumia925.jpg", "gera",
     "kolekcinis Windows Phone; aliuminio rėmas; Carl Zeiss optika", "kai kurios programėlės nebeveikia", "kroviklis", "coffee_f"),
    ("Alcatel mygtukinis telefonas", 3, "demo_alcatel.jpg", "kaip_nauja",
     "baterija laiko savaitę; dideli mygtukai; tinka močiutei; tvirtas kaip plyta", "", "kroviklis", "hot"),
]
_demo_state = {"running": False, "log": []}


def _demo_log(msg):
    _demo_state["log"].append(time.strftime("%H:%M:%S ") + msg)
    _demo_state["log"] = _demo_state["log"][-200:]
    print("[DEMO]", msg, flush=True)


def _is_demo_name(name):
    """True jei dalyvis DB yra contact='demo' (ne vardų blacklist)."""
    if not name:
        return False
    con = db()
    try:
        row = con.execute(
            "SELECT 1 FROM participants WHERE contact='demo' "
            "AND (name=? OR COALESCE(NULLIF(nickname,''),name)=?) LIMIT 1",
            (name, name),
        ).fetchone()
        return bool(row)
    finally:
        con.close()


def _demo_bid(name):
    if AUCTION_LOCKED or not (DEMO_BOTS or PRACTICE_BOTS):
        _demo_log(f"BOTAS NEAKTYVUS: {name} (locked={AUCTION_LOCKED}, bots={DEMO_BOTS}, practice={PRACTICE_BOTS})")
        return None
    _demo_log(f"BOTAS BANDO: {name}")
    con = db()
    try:
        row = con.execute(
            "SELECT pid FROM participants WHERE COALESCE(NULLIF(nickname,''),name)=? "
            "ORDER BY at DESC LIMIT 1", (name,)
        ).fetchone()
        if not row:
            _demo_log(f"BOTAS NERASTAS: {name}")
            return None
        pid = row["pid"]
    finally:
        con.close()
    try:
        result = _place_bid(pid)
        new_price = result.get("current_price")
        _demo_log(f"{name} kelia -> {new_price:.0f} €")
        return new_price
    except Exception as e:
        _demo_log(f"BOTAS KLAIDA {name}: {type(e).__name__}: {e}")
        return None


def _demo_current():
    con = db()
    try:
        lot = maybe_end_lot(con, get_active_lot(con))
        return dict(lot) if lot else None
    finally:
        con.close()


def _demo_run():
    import random
    try:
        names = DEMO_NAMES_F + DEMO_NAMES_M
        con = db()
        now = time.time()
        have = {r["name"] for r in con.execute("SELECT name FROM participants WHERE contact='demo'")}
        for n in names:
            if n not in have:
                con.execute(
                    "INSERT INTO participants (pid, name, nickname, contact, pay_method, at) "
                    "VALUES (?,?,?,?,?,?)",
                    (str(uuid.uuid4()), n, n, "demo", "paypal", now),
                )
        con.commit()
        lot_ids = []
        for title, price, photo, cond, plus, defs, inc, scen in DEMO_LOTS:
            old = con.execute("SELECT id FROM lots WHERE title=? AND status IN ('live','queued') ORDER BY id LIMIT 1",
                              (title,)).fetchone()
            if old:
                lot_ids.append((old["id"], title, scen))
                continue
            src = PHOTOS_DIR / photo
            photo_file = None
            if src.is_file():
                photo_file = uuid.uuid4().hex + ".jpg"
                shutil.copyfile(src, PHOTOS_DIR / photo_file)
            active = maybe_end_lot(con, get_live_lot(con))
            if not active:
                _insert_lot(con, "live", title, "", float(price), 4.0, photo_file,
                            pluses=plus, defects=defs, included=inc, condition=cond)
                # Testo pradžia greita, bet pirmas statymas priklauso žmogui.
                nid = con.execute("SELECT MAX(id) i FROM lots").fetchone()["i"]
                wait_s = max(STARTUP_COUNTDOWN_S, 75)
                st = time.time() + wait_s
                # Pirmas rankinis testas nelaukdamas žmogaus nesibaigia.
                first_window_s = 900 if DEMO_HUMAN else COUNTDOWN_S
                con.execute("UPDATE lots SET starts_at=?, ends_at=? WHERE id=?", (st, st + first_window_s, nid))
                con.commit()
            else:
                m = con.execute("SELECT COALESCE(MAX(queue_order),0) m FROM lots WHERE status='queued'").fetchone()["m"]
                _insert_lot(con, "queued", title, "", float(price), 4.0, photo_file, queue_order=m + 1,
                            pluses=plus, defects=defs, included=inc, condition=cond)
            lot_ids.append((con.execute("SELECT MAX(id) i FROM lots").fetchone()["i"], title, scen))
        # Aktyvus demo lotas laukia žmogaus iki 15 min.; pirmas tikras statymas vėl nustatys 60 s.
        con.execute("UPDATE lots SET ends_at=? WHERE status='live'", (time.time() + 900,))
        con.commit()
        scenario_by_title = {row[0]: row[7] for row in DEMO_LOTS}
        ordered_demo_lots = con.execute(
            "SELECT id,title FROM lots WHERE status IN ('live','queued') "
            "ORDER BY CASE status WHEN 'live' THEN 0 ELSE 1 END, COALESCE(queue_order,0), id"
        ).fetchall()
        lot_ids = [
            (row["id"], row["title"], scenario_by_title[row["title"]])
            for row in ordered_demo_lots if row["title"] in scenario_by_title
        ]
        con.close()
        _demo_log(f"Užregistruota {len(names)} dalyvių, įkelta {len(lot_ids)} lotų" + (" · HUMAN žaidimas" if DEMO_HUMAN else ""))

        def other(exclude=None, female=None):
            pool = DEMO_NAMES_F if female is True else DEMO_NAMES_M if female is False else names
            return random.choice([n for n in pool if n != exclude and n != "Mindaugas"])

        for lot_id, title, scen in lot_ids:
            skip_lot = False
            while True:
                lot = _demo_current()
                if lot and lot["id"] == lot_id and lot["status"] == "live" and lot["starts_at"] and time.time() >= lot["starts_at"] + 4:
                    break
                check = db()
                try:
                    target = check.execute("SELECT status FROM lots WHERE id=?", (lot_id,)).fetchone()
                finally:
                    check.close()
                if not target or target["status"] == "ended":
                    _demo_log(f"PRALEISTA: {title} jau pasibaigė")
                    skip_lot = True
                    break
                time.sleep(1)
            if skip_lot:
                continue
            _demo_log(f"START: {title} ({scen})")
            # Laukti tikro dalyvio pirmo statymo; be žmogaus botai prekybos nepradeda.
            if DEMO_HUMAN:
                _demo_log("LAUKIAMA: tikro dalyvio pirmo statymo")
                human_seen = False
                while True:
                    current = _demo_current() or {}
                    if current.get("id") != lot_id or current.get("status") != "live":
                        _demo_log("Lotas pasikeitė prieš žmogaus statymą — tęsiamas kitas")
                        break
                    lead = current.get("current_bidder")
                    if lead and not _is_demo_name(lead):
                        human_seen = True
                        _demo_log(f"ŽMOGUS STATĖ: {lead} — po 5 s įsijungs botai")
                        time.sleep(5)
                        break
                    time.sleep(1)
                if not human_seen:
                    continue
            # Maratono dalyvės tikrai dalyvauja pirkime, ne vien sąraše.
            # Tarp jų paliekama pauzė, todėl naršyklėje lieka vienas balsas.
            if DEMO_BOTS:
                for featured_name in ("Vanessa", "Oksana"):
                    current = _demo_current() or {}
                    if current.get("status") != "live":
                        break
                    if current.get("current_bidder") != featured_name:
                        _demo_bid(featured_name)
                        _demo_log(f"MARATONAS: {featured_name} kelia kainą")
                    time.sleep(13 if DEMO_HUMAN else 8)

            def burst(k, lo, hi):
                if DEMO_HUMAN:
                    lo, hi = max(lo, 16), max(hi, 24)
                for _ in range(k):
                    cur = _demo_current() or {}
                    # Jei lyderiauja tikras pirkėjas (ne demo) — palaukti
                    lead = cur.get("current_bidder")
                    if DEMO_HUMAN and lead and not _is_demo_name(lead):
                        time.sleep(random.uniform(10, 16))
                    _demo_bid(other(lead))
                    time.sleep(random.uniform(lo, hi))

            if scen == "hot":
                burst(random.randint(4, 6) if DEMO_HUMAN else random.randint(5, 7), 7, 10)
            elif scen in ("coffee_f", "coffee_m"):
                burst(2, 8, 10)
                time.sleep(28 if DEMO_HUMAN else 25)
                lead = (_demo_current() or {}).get("current_bidder")
                _demo_bid(other(lead, female=(scen == "coffee_f")))
                time.sleep(14 if DEMO_HUMAN else 11)
                burst(2, 8, 10)
            elif scen == "duel":
                a, b = other(female=True), other(female=False)
                burst(1, 8, 9)
                for i in range(4 if DEMO_HUMAN else 6):
                    _demo_bid(a if i % 2 == 0 else b)
                    time.sleep(random.uniform(14, 20) if DEMO_HUMAN else random.uniform(8, 10))
            elif scen == "last_second":
                burst(1, 8, 9)
                while True:
                    lot = _demo_current()
                    if not lot or lot["id"] != lot_id or lot["status"] != "live":
                        break
                    if lot["ends_at"] and lot["ends_at"] - time.time() < 5:
                        _demo_bid(other(lot.get("current_bidder")))
                        break
                    time.sleep(0.5)
                burst(1, 8, 9)
            while True:
                lot = _demo_current()
                if not lot or lot["id"] != lot_id or lot["status"] == "ended":
                    break
                time.sleep(2)
            _demo_log(f"PARDUOTA: {title}")
        _demo_log("DEMO baigtas")
    except Exception as e:
        _demo_log(f"KLAIDA: {type(e).__name__}: {e}")
    finally:
        _demo_state["running"] = False


@app.get("/as")
def as_buyer_entry(pid: str = ""):
    """Senoji pirkėjo nuoroda → pagrindinis buyer režimas."""
    params = {"buyer": "1", "fresh": "play"}
    if pid:
        params["pid"] = pid
    return RedirectResponse(url="/?" + urlencode(params), status_code=302)

@app.get("/demo")
def demo_start(k: str = ""):
    if not DEMO_KEY or k != DEMO_KEY:
        raise HTTPException(404, "Not Found")
    if AUCTION_LOCKED:
        raise HTTPException(403, AUCTION_LOCK_MSG)
    if not _demo_state["running"]:
        _demo_state["running"] = True
        _demo_state["log"] = []
        threading.Thread(target=_demo_run, daemon=True).start()
    return HTMLResponse('<meta http-equiv="refresh" content="0;url=/?buyer=1&fresh=play">')


@app.get("/demo/log")
def demo_log(k: str = ""):
    if not DEMO_KEY or k != DEMO_KEY:
        raise HTTPException(404, "Not Found")
    return {"running": _demo_state["running"], "log": _demo_state["log"]}


# ---------- PRAKTIKA: 1000 imitacinių pirkėjų (Vilkas mokosi live) ----------
# Praktika: kelimai NETURI amžinai pratęsti laikmačio (COUNTDOWN_S=60).
# Kitu atveju tas pats lotas (Nokia) kabo valandas — nėra sold / lot_intro / pilno mokymosi.
PRACTICE_MAX_BIDS_PER_LOT = max(6, min(40, int(os.environ.get("PRACTICE_MAX_BIDS_PER_LOT") or "14")))
PRACTICE_MAX_LIVE_S = max(180, min(1800, int(os.environ.get("PRACTICE_MAX_LIVE_S") or "480")))  # 8 min
PRACTICE_END_WAIT_S = float(COUNTDOWN_S) + 25.0  # pauzė > laikmatis → lotas baigiasi

_practice_state = {
    "running": False,
    "seeded": 0,
    "bids": 0,
    "round": 1,
    "reshuffles": 0,
    "last": "",
    "lot_bids": {},  # lot_id -> kelimų šiame live
}


def _practice_log(msg: str) -> None:
    _practice_state["last"] = time.strftime("%H:%M:%S ") + msg
    print("[PRACTICE]", msg, flush=True)


def _practice_name_pool(n: int) -> list[str]:
    """1000 unikalių LT-stiliaus vardų imitacijai (contact=demo)."""
    base = list(dict.fromkeys(DEMO_NAMES_F + DEMO_NAMES_M))
    extra_f = [
        "Gabija", "Emilija", "Kotryna", "Dominyka", "Karolina", "Roberta", "Sandra",
        "Daiva", "Birutė", "Zita", "Aldona", "Janina", "Ramunė", "Aušra", "Reda",
    ]
    extra_m = [
        "Martynas", "Domantas", "Nojus", "Benas", "Kajus", "Herkus", "Arnas",
        "Vladas", "Edmundas", "Stasys", "Petras", "Antanas", "Juozas", "Bronius",
    ]
    base = list(dict.fromkeys(base + extra_f + extra_m))
    out: list[str] = []
    i = 0
    while len(out) < n:
        root = base[i % len(base)]
        suffix = i // len(base)
        name = root if suffix == 0 else f"{root}{suffix + 1}"
        out.append(name)
        i += 1
    return out


def _ensure_practice_bots(n: int | None = None) -> int:
    n = int(n or PRACTICE_BOT_COUNT)
    names = _practice_name_pool(n)
    con = db()
    try:
        have = {
            (r["nickname"] or r["name"] or "").strip()
            for r in con.execute(
                "SELECT name, nickname FROM participants WHERE contact='demo'"
            ).fetchall()
        }
        now = time.time()
        added = 0
        for name in names:
            if name in have:
                continue
            con.execute(
                "INSERT INTO participants (pid, name, nickname, contact, phone, pay_method, at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), name, name, "demo", "", "paypal", now),
            )
            have.add(name)
            added += 1
        # Jei buvo 1000, o dabar 700 — nukerpam perteklių (demo only)
        rows = con.execute(
            "SELECT pid FROM participants WHERE contact='demo' ORDER BY at ASC"
        ).fetchall()
        trimmed = 0
        if len(rows) > n:
            for r in rows[: len(rows) - n]:
                con.execute("DELETE FROM participants WHERE pid=?", (r["pid"],))
                trimmed += 1
        con.commit()
        total = con.execute(
            "SELECT COUNT(*) c FROM participants WHERE contact='demo'"
        ).fetchone()["c"]
        _practice_state["seeded"] = int(total)
        if added or trimmed:
            _practice_log(
                f"Demo: +{added} -{trimmed}; iš viso demo={total} (tikslas {n})"
            )
        return int(total)
    finally:
        con.close()


def _practice_reset_prices_to_start() -> dict:
    """Praktika: kaina atgal nuo starting_price (~20€), ne nuo 3000€."""
    con = db()
    try:
        live = get_live_lot(con)
        info = {"live_id": None, "live_price": None, "queued_reset": 0, "bids_cleared": 0}
        if live:
            start_p = float(live["starting_price"] or 20)
            if start_p < 1:
                start_p = 20.0
            lid = int(live["id"])
            info["live_id"] = lid
            bc = con.execute(
                "SELECT COUNT(*) c FROM bids WHERE lot_id=?", (lid,)
            ).fetchone()["c"]
            con.execute("DELETE FROM bids WHERE lot_id=?", (lid,))
            info["bids_cleared"] = int(bc)
            now = time.time()
            con.execute(
                "UPDATE lots SET current_price=?, current_bidder=NULL, "
                "starts_at=?, ends_at=? WHERE id=?",
                (start_p, now, now + COUNTDOWN_S, lid),
            )
            info["live_price"] = start_p
        qn = 0
        for row in con.execute(
            "SELECT id, starting_price FROM lots WHERE status='queued'"
        ).fetchall():
            sp = float(row["starting_price"] or 20)
            if sp < 1:
                sp = 20.0
            con.execute(
                "UPDATE lots SET current_price=?, current_bidder=NULL WHERE id=?",
                (sp, row["id"]),
            )
            qn += 1
        info["queued_reset"] = qn
        con.commit()
        return info
    finally:
        con.close()


def _practice_pick_bidder(exclude: str | None = None) -> str | None:
    con = db()
    try:
        rows = con.execute(
            "SELECT COALESCE(NULLIF(nickname,''), name) AS n FROM participants "
            "WHERE contact='demo' ORDER BY RANDOM() LIMIT 8"
        ).fetchall()
        for r in rows:
            n = (r["n"] or "").strip()
            if n and n != (exclude or "").strip():
                return n
        return None
    finally:
        con.close()


def _practice_bid_once() -> bool:
    if AUCTION_LOCKED or not PRACTICE_BOTS:
        return False
    if not get_vilkas_stage_on():
        return False
    lot = _demo_current()
    if not lot or lot.get("status") != "live":
        return False
    if lot.get("starts_at") and time.time() < float(lot["starts_at"]):
        return False
    lid = int(lot["id"])
    lot_bids = _practice_state.setdefault("lot_bids", {})
    if int(lot_bids.get(lid) or 0) >= PRACTICE_MAX_BIDS_PER_LOT:
        return False
    starts = float(lot.get("starts_at") or 0)
    if starts and (time.time() - starts) >= PRACTICE_MAX_LIVE_S:
        return False
    name = _practice_pick_bidder(lot.get("current_bidder"))
    if not name:
        return False
    price = _demo_bid(name)
    if price is not None:
        _practice_state["bids"] = int(_practice_state.get("bids") or 0) + 1
        lot_bids[lid] = int(lot_bids.get(lid) or 0) + 1
        return True
    return False


def _practice_wait_lot_end(lot_id: int, reason: str) -> None:
    """Nustok kelti — leisk laikmačiui baigtis, kad būtų sold + kitas lot_intro (pilnas mokymas)."""
    _practice_log(f"Laukiu loto #{lot_id} pabaigos ({reason}) ~{PRACTICE_END_WAIT_S:.0f}s")
    try:
        con = db()
        try:
            row = con.execute(
                "SELECT ends_at FROM lots WHERE id=? AND status='live'", (lot_id,)
            ).fetchone()
            if row and row["ends_at"]:
                target = time.time() + float(COUNTDOWN_S)
                if float(row["ends_at"]) > target + 5:
                    con.execute(
                        "UPDATE lots SET ends_at=? WHERE id=? AND status='live'",
                        (target, lot_id),
                    )
                    con.commit()
            live = get_live_lot(con)
            if live and int(live["id"]) == int(lot_id):
                maybe_end_lot(con, dict(live))
        finally:
            con.close()
    except Exception as e:
        _practice_log(f"ends_at trim warn: {type(e).__name__}: {e}")
    deadline = time.time() + PRACTICE_END_WAIT_S
    while time.time() < deadline and PRACTICE_BOTS and get_vilkas_stage_on():
        cur = _demo_current()
        if not cur or int(cur.get("id") or 0) != int(lot_id) or cur.get("status") != "live":
            break
        try:
            con = db()
            try:
                live = get_live_lot(con)
                if live:
                    maybe_end_lot(con, dict(live))
            finally:
                con.close()
        except Exception:
            pass
        time.sleep(2)
    _practice_state.setdefault("lot_bids", {}).pop(int(lot_id), None)
    try:
        director_tick()
    except Exception:
        pass


def _practice_reshuffle_people(n: int | None = None) -> int:
    """Sumaišom imitacinius dalyvius (at timestamp) — ratas iki viršūnės."""
    import random

    target = int(n if n is not None else PRACTICE_BOT_COUNT)
    total = _ensure_practice_bots(target)
    con = db()
    try:
        rows = con.execute(
            "SELECT pid FROM participants WHERE contact='demo'"
        ).fetchall()
        pids = [r["pid"] for r in rows]
        random.shuffle(pids)
        base = time.time()
        for i, pid in enumerate(pids):
            # at atgaline tvarka → naujas „atsitiktinis“ dalyvių išsidėstymas
            con.execute(
                "UPDATE participants SET at=? WHERE pid=?",
                (base - i * 0.001, pid),
            )
        con.commit()
    finally:
        con.close()
    _practice_state["reshuffles"] = int(_practice_state.get("reshuffles") or 0) + 1
    _practice_state["round"] = int(_practice_state.get("round") or 1) + 1
    _practice_log(
        f"SUMAIŠYTA imitacijų={total} ratas={_practice_state['round']} "
        f"(Vilkas mokosi istisai iki viršūnės / 100%)"
    )
    return total


def _practice_shuffle_queue(con) -> int:
    """Prekės lotuose sukasi aplinkui — atsitiktinė eilės tvarka."""
    import random

    rows = con.execute(
        "SELECT id FROM lots WHERE status='queued'"
    ).fetchall()
    ids = [int(r["id"]) for r in rows]
    if len(ids) < 2:
        return 0
    random.shuffle(ids)
    for i, lid in enumerate(ids, start=1):
        con.execute("UPDATE lots SET queue_order=? WHERE id=?", (i, lid))
    return len(ids)


def _practice_requeue_inventory() -> int:
    """Praktikai: VISI baigti lotai (parduoti + neparsidavę) grįžta į eilę — ratas be sustojimo."""
    con = db()
    try:
        # 1) Neparduoti — visada atgal į ratą
        unsold = int(recycle_unsold_into_queue(con) or 0)
        # 2) Parduoti / ended — irgi atgal (mokymasis iki viršūnės, be sustojimo)
        row_max = con.execute(
            "SELECT COALESCE(MAX(queue_order),0) AS m FROM lots WHERE status='queued'"
        ).fetchone()
        max_order = int(row_max["m"] if row_max else 0)
        sold_back = 0
        for row in con.execute(
            "SELECT id, starting_price FROM lots WHERE status='ended' "
            "ORDER BY COALESCE(resolved_at, 0) ASC, id ASC"
        ).fetchall():
            max_order += 1
            sold_back += 1
            start_p = float(row["starting_price"] or 1)
            if start_p < 1:
                start_p = 20.0
            con.execute(
                "UPDATE lots SET status='queued', queue_order=?, "
                "current_price=?, current_bidder=NULL, starts_at=NULL, ends_at=NULL, "
                "resolved_at=NULL WHERE id=?",
                (max_order, start_p, row["id"]),
            )
        n = unsold + sold_back
        shuffled = _practice_shuffle_queue(con)
        if n or shuffled:
            con.commit()
            _practice_log(
                f"Lotai ratu be sustojimo: neparduoti={unsold} "
                f"parduoti_atgal={sold_back} eilė_sumaišyta={shuffled}"
            )
        if not get_live_lot(con):
            advance_to_next_lot_now(con)
        return n
    finally:
        con.close()


def _practice_loop() -> None:
    """Istisai: 500 imitacijų → sumaišymas + prekės ratu → vėl. Mokymasis iki viršūnės."""
    import random

    _practice_state["running"] = True
    bids_at_round_start = 0
    try:
        _ensure_practice_bots(PRACTICE_BOT_COUNT)
        _practice_requeue_inventory()
        if PRACTICE_AUTO_STAGE and not get_vilkas_stage_on():
            set_vilkas_stage_on(True)
            _practice_log("Stage ON (praktika) — Vilkas scenoje")
            try:
                con = db()
                try:
                    lot = get_live_lot(con) or get_active_lot(con)
                    if lot and lot["status"] == "live":
                        now = time.time()
                        if not lot["starts_at"] or float(lot["starts_at"]) > now + 2:
                            con.execute(
                                "UPDATE lots SET starts_at=?, ends_at=? WHERE id=?",
                                (now, now + COUNTDOWN_S, lot["id"]),
                            )
                            con.commit()
                finally:
                    con.close()
            except Exception as e:
                _practice_log(f"stage timer warn: {type(e).__name__}: {e}")
            try:
                director_tick()
            except Exception:
                pass
        _practice_log(
            f"Praktika ISTISAI iki viršūnės: {PRACTICE_BOT_COUNT} dalyvių, "
            f"prekės ratu be sustojimo, po ~{PRACTICE_BOT_COUNT} kelimų — sumaišymas"
        )
        bids_at_round_start = int(_practice_state.get("bids") or 0)
        while PRACTICE_BOTS:
            try:
                if AUCTION_LOCKED:
                    time.sleep(5)
                    continue
                # F10 OFF — laukiam. NIEKADA nebeįjungiam scenos čia (seniau PRACTICE_AUTO_STAGE
                # per ~3s vėl ON → Mindaugas matė „F10 neveikia / Vilkas grįžta”).
                if not get_vilkas_stage_on():
                    time.sleep(3)
                    continue
                # Naujas ratas: ~500 kelimų → sumaišyk žmones + prekes ratu
                bids_now = int(_practice_state.get("bids") or 0)
                if (bids_now - bids_at_round_start) >= PRACTICE_BOT_COUNT:
                    _practice_reshuffle_people(PRACTICE_BOT_COUNT)
                    _practice_requeue_inventory()
                    bids_at_round_start = bids_now
                    try:
                        director_tick()
                    except Exception:
                        pass
                lot = _demo_current()
                if not lot or lot.get("status") != "live":
                    _practice_requeue_inventory()
                    time.sleep(2)
                    continue
                if lot.get("starts_at") and time.time() < float(lot["starts_at"]):
                    # Kavos / intro langas — neliečiam, kad Vilkas spėtų lot_intro
                    time.sleep(2)
                    continue
                lid = int(lot["id"])
                lot_bids = _practice_state.setdefault("lot_bids", {})
                n_lot = int(lot_bids.get(lid) or 0)
                starts = float(lot.get("starts_at") or 0)
                live_for = (time.time() - starts) if starts else 0.0
                # Užtenka kelimų / per ilgai live → baigiam lotą → sold + kita prekė + intro
                if n_lot >= PRACTICE_MAX_BIDS_PER_LOT or live_for >= PRACTICE_MAX_LIVE_S:
                    why = (
                        f"max {PRACTICE_MAX_BIDS_PER_LOT} kelimų"
                        if n_lot >= PRACTICE_MAX_BIDS_PER_LOT
                        else f"max {PRACTICE_MAX_LIVE_S}s live"
                    )
                    _practice_wait_lot_end(lid, why)
                    continue
                # Trumpa kova (2–4 kelimai), tada ILGA pauzė (>60s) — kitaip laikmatis niekada nesibaigia
                burst = random.randint(2, 4)
                did = 0
                for _ in range(burst):
                    if _practice_bid_once():
                        did += 1
                    time.sleep(random.uniform(2.0, 5.0))
                    n_lot = int(lot_bids.get(lid) or 0)
                    if n_lot >= PRACTICE_MAX_BIDS_PER_LOT:
                        break
                # Director: joke / nudge / guitar / phone turi erdvės tarp kelimų
                try:
                    director_tick()
                except Exception:
                    pass
                pause = random.uniform(PRACTICE_END_WAIT_S, PRACTICE_END_WAIT_S + 25.0)
                _practice_log(
                    f"Pauzė mokymui {pause:.0f}s (lot #{lid}, burst={did}, "
                    f"lot_bids={lot_bids.get(lid, 0)}, total={_practice_state.get('bids')})"
                )
                time.sleep(pause)
                # Po ilgos pauzės — jei dar live ir jau max kelimų, uždarom
                lot2 = _demo_current()
                if lot2 and int(lot2.get("id") or 0) == lid and lot2.get("status") == "live":
                    n2 = int((_practice_state.get("lot_bids") or {}).get(lid) or 0)
                    if n2 >= PRACTICE_MAX_BIDS_PER_LOT or (
                        float(lot2.get("starts_at") or 0)
                        and time.time() - float(lot2["starts_at"]) >= PRACTICE_MAX_LIVE_S
                    ):
                        _practice_wait_lot_end(lid, "po pauzės")
            except Exception as e:
                _practice_log(f"loop klaida: {type(e).__name__}: {e}")
                time.sleep(5)
    finally:
        _practice_state["running"] = False
        _practice_log("Praktika sustojo")


@app.get("/api/practice/status")
def api_practice_status():
    return {
        "ok": True,
        "practice_bots": PRACTICE_BOTS,
        "practice_bot_count": PRACTICE_BOT_COUNT,
        "public_registration_open": PUBLIC_REGISTRATION_OPEN,
        "seeded": _practice_state.get("seeded"),
        "bids": _practice_state.get("bids"),
        "round": _practice_state.get("round"),
        "reshuffles": _practice_state.get("reshuffles"),
        "running": _practice_state.get("running"),
        "last": _practice_state.get("last"),
        "stage": get_vilkas_stage_on(),
        "endless": True,
        "goal": "500 dalyvių · prekės ratu be sustojimo · mokymasis iki viršūnės",
    }


@app.post("/api/admin/practice_round")
async def api_admin_practice_round(request: Request):
    """500 žmonių, sumaišymas, prekės ratu, kainos nuo starting_price — praktika iki viršūnės."""
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    want = body.get("count")
    try:
        n = max(50, min(5000, int(want if want is not None else PRACTICE_BOT_COUNT)))
    except Exception:
        n = PRACTICE_BOT_COUNT
    total = _ensure_practice_bots(n)
    shuffled = _practice_reshuffle_people(n)
    requeued = _practice_requeue_inventory()
    prices = _practice_reset_prices_to_start()
    _practice_state["bids"] = 0
    _practice_log(
        f"PRACTICE ROUND: demo={total} shuffled={shuffled} requeued={requeued} "
        f"live_price={prices.get('live_price')} queued={prices.get('queued_reset')}"
    )
    return {
        "ok": True,
        "demo_count": total,
        "target": n,
        "shuffled": shuffled,
        "requeued": requeued,
        "prices": prices,
        "stage": get_vilkas_stage_on(),
        "goal": "prekės ratu be sustojimo · 500 dalyvių · mokymasis iki viršūnės",
    }


if PRACTICE_BOTS and BACKGROUND_LOOPS_ENABLED:
    threading.Thread(target=_practice_loop, daemon=True, name="vilkas-practice").start()


# ---------- frontend ----------

INDEX_HTML = r"""<!doctype html><html lang="lt"><head><meta charset="utf-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<!-- Telefonas = tas pats desktop vaizdas (ne atskiras mobile layout) -->
<meta name="viewport" content="width=1280">
<title>Penktadienio aukcionas — gyvas internetinis aukcionas Lietuvoje</title>
<meta name="description" content="Penktadienio aukcionas (penktadienioaukcionas.lt) — gyvas internetinis aukcionas Lietuvoje. Telefonai ir daiktai, realūs statymai, vedėjas Vilkas. Dalyvaukite kiekvieną penktadienį.">
<meta name="keywords" content="penktadienio aukcionas, penktadienioaukcionas.lt, internetinis aukcionas, gyvas aukcionas Lietuva, telefonų aukcionas">
<meta name="robots" content="index, follow">
<meta name="google-site-verification" content="huelEeUtXk1teqkZRd0GH82fXTeSlP414jS5UxuP7OY">
<link rel="canonical" href="https://penktadienioaukcionas.lt/">
<meta property="og:type" content="website">
<meta property="og:locale" content="lt_LT">
<meta property="og:url" content="https://penktadienioaukcionas.lt/">
<meta property="og:title" content="Penktadienio aukcionas — gyvas internetinis aukcionas">
<meta property="og:description" content="Gyvas internetinis aukcionas Lietuvoje. Realūs statymai, telefonai ir daiktai. penktadienioaukcionas.lt">
<meta property="og:site_name" content="Penktadienio aukcionas">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="Penktadienio aukcionas">
<meta name="twitter:description" content="Gyvas internetinis aukcionas Lietuvoje — penktadienioaukcionas.lt">
<link rel="icon" href="data:,">
<script>
/* Šveicariškas laikrodis: serveris naujesnis → automatiškai perkrauna (be Ctrl+F5) */
(function(){
  var PAGE_BUILD='__BUILD_ID__';
  window.PAGE_BUILD=PAGE_BUILD;
  try{
    if(navigator.serviceWorker){
      navigator.serviceWorker.getRegistrations().then(function(rs){
        rs.forEach(function(r){ try{ r.unregister(); }catch(e){} });
      });
    }
  }catch(e){}
  function check(){
    fetch('/api/build',{cache:'no-store'}).then(function(r){ return r.json(); }).then(function(d){
      if(!d || !d.id || d.id===PAGE_BUILD) return;
      var u=new URL(location.href);
      u.searchParams.set('_v', d.id);
      location.replace(u.toString());
    }).catch(function(){});
  }
  check();
  setInterval(check, 45000);
})();
</script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root{--bg:#14100c;--surface:#1f1811;--surface-2:#2a2018;--surface-3:#362a1e;--border:#40331f;--text:#f3ead9;--text-dim:#b9a88f;--text-faint:#7d6f5b;--accent:#ff7a33;--accent-2:#ffb347;--gold:#e3b23c;--good:#4caf7d;--good-bg:#1c2c22;}
*{box-sizing:border-box;}
/* Visur desktop drobė — telefonas zoom'ina visą 1280px layout */
html{min-width:1280px;width:1280px;max-width:1280px;overflow-x:hidden;}
body{margin:0;background:radial-gradient(ellipse 900px 500px at 50% -10%,#2a1f14 0%,transparent 60%),var(--bg);color:var(--text);font-family:'Archivo',sans-serif;display:flex;justify-content:center;padding:28px 250px 120px 290px;min-height:100vh;min-width:1280px;width:1280px;max-width:1280px;box-sizing:border-box;overflow-x:hidden;}
/* Be atskiro mobile body padding — visada desktop */
body.cover-mode{padding-top:8px;}
.stage{width:100%;max-width:560px;position:relative;overflow:visible;z-index:5;}
.brand{
  /* ATKURTA iš SUREGULIUOTA_LAYOUT — tavo paskutiniai reguliavimai */
  margin:4px auto 22px;text-align:center;position:relative;z-index:6;
  width:100%;max-width:620px;left:auto;
  /* buvo -20%; +30% dešinėn → +10% (įžanga / scenoje) */
  transform:translateX(-6%);
  box-sizing:border-box;
}
.brand-top{
  display:flex;flex-direction:row;align-items:center;justify-content:center;
  gap:8px;flex-wrap:nowrap;width:100%;max-width:100%;margin:0 0 8px;
  box-sizing:border-box;
}
.brand-name,.brand-evening{
  font-family:'Archivo',sans-serif;font-weight:300;font-size:22px!important;letter-spacing:.1em;
  color:#ffffff;line-height:1.15;margin:0;text-transform:uppercase;
  text-shadow:0 0 3px #fff,0 0 8px rgba(255,255,255,.95),0 0 18px rgba(255,255,255,.6),0 0 32px rgba(210,230,255,.35);
  animation:neonWhiteGlow 4s ease-in-out infinite alternate;
}
.brand-name{
  flex:0 1 auto;white-space:nowrap;min-width:0;
  font-size:24.2px!important;
  /* buvo -12%; +30% dešinėn → +18% */
  transform:translateX(-22%);
}
/* Badge VIRŠUJE — ispletimas +15% kaire / +5% desine */
.brand-top .radio-badge{
  position:relative;flex:0 0 auto;margin:0;width:auto;max-width:170px;max-height:42px;
  overflow:hidden;box-sizing:border-box;z-index:7;
  transform:translate(-40%,23%);
  padding-left:6px;padding-right:2px;
}
.brand-top .radio-choice{min-width:158px;min-height:36px;padding:2px 10px 2px 18px;}
.brand-top .radio-choice .rb-top{font-size:8px;letter-spacing:.1em;}
.brand-top .radio-choice .rb-mid{font-size:11px;}
@keyframes neonWhiteGlow{
  0%{text-shadow:0 0 2px #fff,0 0 6px rgba(255,255,255,.85),0 0 14px rgba(255,255,255,.5),0 0 26px rgba(210,230,255,.25);opacity:.95;}
  100%{text-shadow:0 0 4px #fff,0 0 10px rgba(255,255,255,1),0 0 24px rgba(255,255,255,.8),0 0 42px rgba(210,230,255,.45);opacity:1;}
}
.brand-sub{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:rgba(235,240,250,.6);margin:0;}
.brand-evening{display:inline-block;font-size:20.9px!important;transform:translate(-103%,-23%);}
.brand-evening .brand-time{letter-spacing:.1em;}
/* Įžanga + scena: visas blokas (pavadinimas + vakare 20:00) +30% dešinėn */
body.cover-mode .brand,
body:not(.cover-mode) .brand{transform:translateX(-6%);}
body.cover-mode .brand-name,
body:not(.cover-mode) .brand-name{transform:translateX(-22%);}
body.cover-mode .brand-evening,
body:not(.cover-mode) .brand-evening{transform:translate(-103%,-23%);}
@media (max-width:899px){
  .brand{width:100%;max-width:620px;left:auto;transform:translateX(-6%);}
  .brand-name{font-size:24.2px!important;letter-spacing:.1em;transform:translateX(-22%);}
  .brand-evening{font-size:20.9px!important;letter-spacing:.1em;transform:translate(-103%,-23%);}
}
.lot-header{display:none!important;}
.host-controls,#btnVoice{display:none!important;}
.participants-panel{
  position:fixed;left:8px;top:8px;bottom:8px;z-index:70;box-sizing:border-box;
  /* 228px — laukai PILNI; vardai atskirai fit-content (ne platus juostos) */
  width:228px;max-width:228px;height:auto;max-height:none;overflow:hidden;
  background:#0a0a0a;border:1px solid rgba(255,180,80,.35);
  border-radius:12px;padding:8px;
  box-shadow:0 12px 32px rgba(0,0,0,.65);
  color:#f3e8d3;font-family:system-ui,'Segoe UI',sans-serif;
  display:flex;flex-direction:column;gap:8px;
}
.participants-panel .pp-count{
  font-family:'Anton',sans-serif;font-size:22px;letter-spacing:.03em;
  color:#39ff6a;text-shadow:0 0 10px rgba(57,255,106,.45);line-height:1.1;
}
.participants-panel .pp-label{
  font-size:11px;letter-spacing:.08em;text-transform:uppercase;
  color:rgba(243,232,211,.55);margin-top:-4px;
}
.participants-panel .pp-list{
  overflow:auto;flex:1 1 auto;min-height:80px;max-height:none;
  display:flex;flex-direction:column;gap:3px;
  scrollbar-width:thin;scrollbar-color:#3a3126 transparent;
}
.participants-panel .pp-name{
  font-size:13px;line-height:1.35;color:#e8dcc8;
  padding:3px 6px;border-radius:6px;background:rgba(255,255,255,.04);
  display:inline-block;width:fit-content;max-width:100%;
  box-sizing:border-box;
}
.participants-panel .pp-name.me{background:rgba(57,255,106,.18);color:#7dffa8;border:1px solid rgba(57,255,106,.35);}
.participants-panel .pp-empty{font-size:12px;color:rgba(243,232,211,.45);padding:4px 2px;}
.participants-panel .pp-reg{
  border-top:1px solid rgba(255,180,80,.25);padding-top:10px;margin-top:2px;
  display:flex;flex-direction:column;gap:6px;flex:0 0 auto;
}
.participants-panel .pp-reg-title{
  font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#ffb347;font-weight:700;
}
.participants-panel .pp-reg input{
  width:100%;box-sizing:border-box;background:#161210;border:1px solid rgba(255,180,80,.35);
  color:#f3e8d3;font-size:10.5px;padding:8px 8px;border-radius:8px;outline:none;
}
.participants-panel .pp-reg button#joinBtn{
  font-family:'JetBrains Mono',monospace;font-weight:700;font-size:14px;letter-spacing:.06em;text-transform:uppercase;
  background:linear-gradient(180deg,#7dff9a,#39ff6a 55%,#1ecf4a)!important;
  color:#0a0a0a!important;
  border:1px solid rgba(125,255,154,.8)!important;
  padding:13px 10px;border-radius:10px;cursor:pointer;
  text-shadow:none!important;
  -webkit-font-smoothing:antialiased;
  box-shadow:0 0 14px rgba(57,255,106,.45),inset 0 1px 0 rgba(255,255,255,.4);
  filter:none!important;opacity:1!important;
}
.participants-panel .pp-reg button#joinBtn:hover{filter:brightness(1.05)!important;}
.participants-panel .pp-reg button#joinBtn:disabled{
  background:#2a332e!important;border-color:#3d4741!important;color:#6a756e!important;
  box-shadow:none;cursor:default;opacity:1!important;filter:none!important;
}
.participants-panel .pp-bid-wrap{margin-top:8px;flex:0 0 auto;}
.participants-panel .bid-btn{
  width:100%!important;font-size:16px!important;padding:16px 10px!important;border-radius:12px!important;margin:0!important;
  display:flex!important;flex-direction:row;align-items:center;justify-content:center;gap:0;
  min-height:56px;
  font-family:'JetBrains Mono',monospace!important;letter-spacing:.05em;text-transform:uppercase;font-weight:800;
  color:#0a0a0a!important;
  background:linear-gradient(180deg,#7dff9a,#39ff6a 55%,#1ecf4a)!important;
  border:2px solid rgba(125,255,154,.95)!important;
  text-shadow:none!important;
  -webkit-font-smoothing:antialiased;
  box-shadow:0 0 18px rgba(57,255,106,.55),inset 0 1px 0 rgba(255,255,255,.45)!important;
  animation:none!important;
  filter:none!important;opacity:1!important;
}
.participants-panel .bid-btn:not(:disabled):hover{filter:brightness(1.05)!important;}
.participants-panel .bid-btn:disabled{
  background:linear-gradient(180deg,#3a4a40,#2a332e 55%,#222a26)!important;
  border-color:#4a5a50!important;color:#c8d4cc!important;
  box-shadow:none!important;animation:none!important;filter:none!important;opacity:1!important;
  cursor:default;
}
.participants-panel .bid-btn #bidLabel{color:inherit!important;text-shadow:none!important;line-height:1.25;text-align:center;}
.participants-panel .bid-btn:not(:disabled) #bidLabel{color:#0a0a0a!important;}
.participants-panel .bid-btn .step,
.participants-panel .bid-btn .bid-time{display:none!important;}
.participants-panel .pp-reg-note{font-size:11px;color:rgba(243,232,211,.7);min-height:14px;}
.participants-panel .pp-done{font-size:12px;color:#7dffa8;line-height:1.35;}
.radio-badge{
  display:inline-flex;flex-direction:column;align-items:center;justify-content:center;margin:0;
  background:rgba(8,8,8,.92);border:1px solid rgba(255,209,102,.6);
  border-radius:10px;padding:3px;gap:1px;pointer-events:auto;z-index:100;
  box-shadow:0 0 0 4px rgba(0,0,0,.85),0 0 14px rgba(255,209,102,.28);
  box-sizing:border-box;overflow:hidden;
}
.radio-choice{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;
  border:0;border-radius:7px;min-width:158px;min-height:56px;max-width:100%;width:100%;
  padding:5px 11px 5px 20px;box-sizing:border-box;
  background:rgba(8,8,8,.92);cursor:pointer;white-space:normal;text-align:center;line-height:1.08;
  overflow:hidden;}
.radio-choice:hover{background:rgba(255,209,102,.14);}
.radio-choice.active{background:rgba(8,8,8,.92);box-shadow:inset 0 0 10px rgba(255,209,102,.18);}
.radio-choice .rb-top{font-family:Georgia,'Times New Roman',serif;font-weight:700;font-size:12px;
  letter-spacing:.14em;text-transform:uppercase;color:#ffd166;text-shadow:0 0 8px rgba(255,209,102,.55);
  max-width:100%;overflow:hidden;text-overflow:clip;white-space:nowrap;}
.radio-choice .rb-mid{font-family:Georgia,'Times New Roman',serif;font-weight:700;font-size:16px;
  letter-spacing:.01em;text-transform:uppercase;color:#ffd166;text-shadow:0 0 10px rgba(255,209,102,.7);
  max-width:100%;overflow:hidden;text-overflow:clip;white-space:nowrap;}
.radio-choice .rb-sub{font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:12px;
  letter-spacing:.24em;text-transform:uppercase;color:#ffd166;text-shadow:0 0 8px rgba(255,209,102,.55);}
body.auction-locked .participants-panel .bid-btn{opacity:1!important;filter:none!important;pointer-events:auto;}
.participants-panel .pp-reg-note{font-size:11px;color:#d4c4a8;min-height:14px;line-height:1.3;}
.participants-panel .pp-done{font-size:12px;color:#7dffa8;padding:6px 0 2px;display:flex;flex-direction:column;gap:6px;}
.pp-done-msg{line-height:1.35;}
.pp-change-reg{
  border:1px solid rgba(255,180,80,.4);background:rgba(255,180,80,.1);color:#ffb347;
  border-radius:8px;padding:6px 8px;font-size:11px;font-weight:700;cursor:pointer;width:100%;
}
.pp-change-reg:hover{background:rgba(255,180,80,.2);}
.participants-panel.registered{max-height:none;}
.participants-panel.registered .pp-reg{display:none!important;}
.participants-panel.registered .pp-list{max-height:none;}
.pp-pay-title,.pp-pay-opts{display:none!important;}
.pay-box .pay-private{display:none;margin-top:8px;padding:8px 10px;border-radius:10px;background:rgba(57,255,106,.08);border:1px solid rgba(57,255,106,.28);}
.pay-box .pay-private.show{display:block;}
.pay-box .pay-private .ppv-mail{font-family:'JetBrains Mono',monospace;font-size:13px;color:#7dffa8;word-break:break-all;margin:4px 0;}
.pay-box .pay-wait{font-size:12px;line-height:1.4;color:rgba(243,232,211,.75);}
@media (max-width:640px){
  .participants-panel{box-sizing:border-box;width:228px;max-width:228px;height:auto;left:8px;top:6px;bottom:auto;padding:8px;max-height:48vh;}
  .participants-panel .pp-count{font-size:16px;}
  .participants-panel .pp-name{font-size:11px;padding:2px 4px;}
  .participants-panel .pp-list{max-height:22vh;min-height:42px;}
  .participants-panel.reg-collapsed .pp-reg>*:not(.pp-reg-title){display:none!important;}
  .participants-panel.reg-collapsed .pp-reg{padding-top:6px;}
  .participants-panel .pp-reg-title{cursor:pointer;padding:5px;border-radius:7px;background:rgba(255,179,71,.12);}
  .participants-panel.reg-collapsed .pp-reg-title::after{content:' · atidaryti';color:#7dffa8;}
  .participants-panel:not(.reg-collapsed):not(.registered){
    left:0;right:0;bottom:0;top:auto;width:100%;max-width:none;
    height:auto;max-height:70vh;overflow:auto;z-index:85;
    border-radius:16px 16px 0 0;padding:12px 12px 16px;
    box-shadow:0 -12px 40px rgba(0,0,0,.65);
  }
  .participants-panel:not(.reg-collapsed):not(.registered) .pp-list{max-height:18vh;min-height:36px;}
  .participants-panel.registered{width:min(230px,64vw);max-height:112px;}
  .participants-panel.registered .pp-list{min-height:0;max-height:36px;flex-direction:row;overflow-x:auto;overflow-y:hidden;}
  .participants-panel.registered .pp-name{white-space:nowrap;flex:0 0 auto;}
}
.lock-banner{display:none;background:linear-gradient(135deg,#3a2a12,#2a1f0e);border:1px solid #c9a227;color:#f5e6b8;font-weight:600;font-size:14px;line-height:1.45;padding:14px 16px;border-radius:12px;margin-bottom:14px;text-align:center;}
.lock-banner.show{display:block;}
.lock-banner b{color:#ffe08a;}
body.auction-locked #bidBtn.tiers-skip,body.auction-locked .tiers,body.auction-locked .hint{opacity:.45;}
body.auction-locked .tiers,body.auction-locked .hint{pointer-events:none;}
body.auction-locked .participants-panel .pp-reg,
body.auction-locked .participants-panel .pp-bid-wrap{opacity:1;pointer-events:auto;}
body.auction-locked .participants-panel .bid-btn{opacity:1;}
body.auction-locked .pay-box{display:none!important;}
body.auction-locked .sold-banner{display:none!important;}
body.auction-locked .pay-strip{display:block;}
.pay-strip{
  position:fixed;top:10px;right:14px;z-index:72;
  width:220px;max-width:220px;box-sizing:border-box;
  margin:0;padding:6px 6px 7px;border-radius:10px;
  background:transparent;
  border:0;
  box-shadow:none;
  backdrop-filter:none;
  overflow:visible;
}
/* Taisyklės — tik paspaudus; NIEKADA ne ant telefono/scenos (Vilkas 8) */
.auction-quick-rules{
  display:none;position:absolute;top:calc(100% + 6px);right:0;left:auto;
  width:min(240px,78vw);max-height:min(52vh,380px);overflow:auto;box-sizing:border-box;
  padding:28px 10px 10px;border-radius:12px;background:rgba(10,10,10,.96);
  border:1px solid rgba(255,180,80,.35);box-shadow:0 10px 28px rgba(0,0,0,.6);
  color:#e8dcc8;text-align:left;z-index:74;
}
.auction-quick-rules.open{display:block;}
.aqr-toggle{
  display:block;width:100%;margin-top:5px;border:1px solid rgba(255,180,80,.35);
  background:rgba(255,255,255,.06);color:#ffb347;border-radius:7px;padding:4px 7px;
  font-size:9px;font-weight:700;letter-spacing:.04em;cursor:pointer;text-align:center;
}
.aqr-toggle:hover{background:rgba(255,180,80,.14);}
.aqr-title{font-family:'Anton',sans-serif;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#ffb347;margin-bottom:5px;}
.auction-quick-rules ul{margin:0 0 6px;padding-left:15px;display:flex;flex-direction:column;gap:2px;}
.auction-quick-rules li{font-size:10px;line-height:1.3;color:#e8dcc8;}
.aqr-contact{font-size:10px;line-height:1.4;color:#d4c4a8;border-top:1px solid rgba(255,180,80,.2);padding-top:5px;}
.aqr-contact a{color:#7dffa8;text-decoration:none;word-break:break-all;}
.rules-box{display:none!important;}
.pay-strip-title{
  font-family:'Anton',sans-serif;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:#ffffff;margin:0 0 5px;text-align:center;line-height:1.25;
  text-shadow:0 0 8px rgba(255,255,255,.6),0 0 20px rgba(255,255,255,.35);
}
.pay-row{display:flex;flex-direction:row;flex-wrap:wrap;align-items:center;gap:4px;width:100%;}
.pay-badges{display:flex;flex-direction:row;flex-wrap:wrap;gap:4px;align-items:center;justify-content:center;width:100%;}
.pay-badge{
  display:inline-flex;align-items:center;justify-content:center;
  min-height:20px;padding:0 6px;border-radius:6px;border:0;cursor:pointer;
  font-family:'Archivo',sans-serif;font-weight:800;font-size:8px;letter-spacing:.03em;
  text-transform:none;color:#fff;transition:transform .15s,filter .15s;white-space:nowrap;
}
.pay-badge:hover{transform:translateY(-1px);filter:brightness(1.08);}
.pay-badge:active{transform:translateY(0);}
.pay-badge.paypal{background:linear-gradient(135deg,#003087,#009cde);box-shadow:0 2px 8px rgba(0,156,222,.3);}
.pay-badge.skrill{background:linear-gradient(135deg,#6b0f4a,#c4126d);box-shadow:0 2px 8px rgba(196,18,109,.3);}
.pay-badge.neteller{background:linear-gradient(135deg,#5a8f1a,#8dc63f);color:#0a0a0a;box-shadow:0 2px 8px rgba(141,198,63,.3);}
.pay-badge.paysafe{background:linear-gradient(135deg,#0b5cab,#00a3e0);box-shadow:0 2px 8px rgba(0,163,224,.3);}
/* Senas pay-row badge — jei liktų, nerodom (tikras = .brand-top) */
.pay-row .radio-badge{display:none!important;}
.aqr-toggle{
  display:block;width:fit-content;max-width:100%;margin:6px 0 0 auto;border:1px solid rgba(255,255,255,.28);
  background:rgba(255,255,255,.05);color:#e8e8e8;border-radius:7px;padding:5px 10px;
  font-size:12px;font-weight:700;letter-spacing:.04em;cursor:pointer;text-align:center;
  transform:none;box-sizing:border-box;
}
.pay-strip-detail{
  position:absolute;top:calc(100% + 6px);right:0;width:min(260px,72vw);
  margin-top:0;padding:28px 10px 8px;border-radius:10px;background:rgba(14,11,10,.96);
  border:1px solid rgba(255,180,80,.3);display:none;z-index:73;
  box-shadow:0 10px 28px rgba(0,0,0,.55);
}
.pay-strip-detail.on{display:block;}
.ui-close-x{
  position:absolute;top:4px;right:6px;z-index:5;
  border:0;background:rgba(255,255,255,.12);color:#fff;
  width:28px;height:28px;border-radius:8px;cursor:pointer;
  font-size:16px;line-height:1;padding:0;font-weight:700;
}
.ui-close-x:hover{background:rgba(255,80,60,.45);}
.pay-strip-detail .psd-name{font-size:10px;font-weight:700;color:#ffb347;text-transform:uppercase;letter-spacing:.06em;margin:0 0 4px;}
.pay-strip-detail .psd-mail{
  font-family:'JetBrains Mono',monospace;font-size:11px;color:#f3ead9;word-break:break-all;
  display:flex;flex-wrap:wrap;gap:6px;align-items:center;
}
.pay-strip-detail .psd-mail a{color:#7dffa8;text-decoration:none;}
.pay-strip-detail .psd-copy{
  border:1px solid rgba(57,255,106,.45);background:rgba(57,255,106,.12);color:#7dffa8;
  border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;cursor:pointer;
}
.pay-strip-detail .psd-hint{margin:6px 0 0;font-size:10px;line-height:1.4;color:rgba(243,232,211,.6);}
.pay-list .pay-li-badge{display:inline-block;font-size:10px;font-weight:800;letter-spacing:.04em;padding:2px 7px;border-radius:5px;margin-right:6px;vertical-align:middle;}
.pay-list .pay-li-badge.paypal{background:#009cde;color:#fff;}
.pay-list .pay-li-badge.skrill{background:#c4126d;color:#fff;}
.pay-list .pay-li-badge.neteller{background:#8dc63f;color:#0a0a0a;}
.pay-list .pay-li-badge.paysafe{background:#00a3e0;color:#fff;}
@media (max-width:720px){
  /* Su viewport 1280 — tie patys dydžiai, be atskiro mobile layout */
  .pay-strip{top:10px;right:14px;left:auto;width:220px;max-width:220px;padding:6px 6px 7px;overflow:visible;}
  .brand{padding:0;max-width:620px;width:100%;margin:4px auto 22px;}
  body.cover-mode .brand{margin:4px auto 22px;}
  .participants-panel.registered{top:8px;left:8px;}
  .pay-strip-title{font-size:11px;margin-bottom:4px;}
  .pay-badge{min-height:20px;font-size:8px;padding:0 6px;border-radius:6px;}
  .pay-badges,.pay-row{gap:4px;flex-wrap:wrap;}
  .auction-quick-rules{width:min(220px,88vw);padding:26px 8px 8px;}
  .aqr-title{font-size:9px;margin-bottom:3px;}
  .auction-quick-rules li,.aqr-contact{font-size:8px;line-height:1.25;}
  .aqr-toggle{font-size:10px;padding:4px 8px;}
}
.lot-tag{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.12em;color:var(--accent-2);background:rgba(255,122,51,.12);border:1px solid rgba(255,122,51,.35);padding:4px 10px;border-radius:999px;text-transform:uppercase;}
.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-right:6px;box-shadow:0 0 0 0 rgba(255,122,51,.6);animation:pulse 1.6s infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,122,51,.55);}70%{box-shadow:0 0 0 7px rgba(255,122,51,0);}100%{box-shadow:0 0 0 0 rgba(255,122,51,0);}}
.viewers{font-family:'JetBrains Mono',monospace;font-size:12px;color:#39ff6a;text-shadow:0 0 8px rgba(57,255,106,.65),0 0 2px rgba(57,255,106,.9);font-weight:600;}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:18px;overflow:hidden;overflow-x:hidden;box-shadow:0 28px 48px -36px rgba(0,0,0,.7);position:relative;isolation:isolate;}
.panel.empty-lot{display:none!important;border:0!important;box-shadow:none!important;height:0!important;margin:0!important;padding:0!important;}
.art{display:flex;flex-direction:row;flex-wrap:nowrap;align-items:stretch;gap:0;background:linear-gradient(180deg,#211a12 0%,#1a140e 100%);border-bottom:1px solid var(--border);padding-bottom:0;overflow:hidden;max-width:100%;}
.panel.empty-lot .art{display:none!important;border:0!important;padding:0!important;height:0!important;}
.art img{flex:0 0 75%;min-width:0;width:75%;max-height:255px;object-fit:contain;object-position:0% center;display:block;margin:0;padding:0;border:0;}
.art-empty{padding:48px 20px;text-align:center;color:var(--text-faint);font-size:13px;line-height:1.6;}
.item-body{padding:20px 22px 88px;}
.item-title{font-size:19px;font-weight:700;margin:0 0 3px;}
.item-meta{font-size:13px;color:var(--text-dim);margin:0 0 14px;}
.item-meta b{color:var(--text);font-weight:600;}
.desc-box{background:var(--surface-2);border:1px solid var(--border);border-radius:12px;padding:13px 15px;margin-bottom:20px;}
.desc-label{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint);margin-bottom:6px;}
.desc-text{margin:0;font-size:13.5px;line-height:1.6;color:var(--text);white-space:pre-wrap;}
.price-row{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:6px;}
.price-bid{
  flex:1 1 auto;max-width:220px;min-height:58px;margin:0 2px 3px;
  font-family:'Anton',sans-serif!important;font-size:18px!important;letter-spacing:.04em;
  color:#0a0a0a!important;background:linear-gradient(180deg,#7dff9a,#39ff6a 55%,#1ecf4a)!important;
  border:2px solid rgba(125,255,154,.95)!important;border-radius:12px!important;
  box-shadow:0 0 18px rgba(57,255,106,.42),inset 0 1px 0 rgba(255,255,255,.45)!important;
}
.price-bid:not(:disabled):hover{filter:brightness(1.08);transform:translateY(-1px);}
.price-bid:disabled{background:linear-gradient(180deg,#3a4a40,#2a332e 55%,#222a26)!important;color:#c8d4cc!important;opacity:1!important;}
.price-label{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint);}
.price{font-family:'Anton',sans-serif;font-size:clamp(40px,12vw,56px);line-height:1;color:var(--gold);white-space:nowrap;}
.price small{font-size:.42em;color:var(--text-dim);font-family:'Archivo',sans-serif;font-weight:600;}
.timer-ring{position:relative;width:76px;height:76px;flex:none;}
.timer-ring svg{transform:rotate(-90deg);width:100%;height:100%;}
.timer-ring circle{fill:none;stroke-width:6;}
.timer-track{stroke:var(--surface-3);}
.timer-fill{stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .3s linear,stroke .3s linear;}
.timer-num{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px;}
@media (max-width:640px){
  .price-row{gap:8px;align-items:center;}
  .price-bid{font-size:14px!important;min-height:52px;padding:8px!important;}
  .timer-ring{width:68px;height:68px;}
}
.bidder-line{font-size:13px;color:var(--text-dim);margin:10px 0 18px;min-height:18px;}
.bidder-line b{color:var(--accent-2);}
.reg-form{display:flex;flex-direction:column;gap:8px;margin-bottom:6px;}
.reg-form input{background:var(--surface-2);border:1px solid var(--border);color:var(--text);font-family:'Archivo',sans-serif;font-size:14px;padding:11px 13px;border-radius:10px;outline:none;width:100%;}
.reg-form button{font-weight:700;font-size:14px;background:var(--surface-3);color:var(--text);border:1px solid var(--border);padding:11px;border-radius:10px;cursor:pointer;}
.reg-note{font-size:11.5px;color:var(--accent-2);margin:0 0 14px;min-height:14px;}
.bid-btn{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;font-weight:700;font-size:17px;color:#1a1006;background:linear-gradient(180deg,var(--accent-2),var(--accent));border:none;padding:16px;border-radius:12px;cursor:pointer;box-shadow:0 8px 22px -8px rgba(255,122,51,.55);}
.bid-btn:disabled{opacity:.5;cursor:not-allowed;box-shadow:none;}
.bid-btn .step{font-family:'JetBrains Mono',monospace;font-size:13px;background:rgba(0,0,0,.18);padding:3px 9px;border-radius:999px;}
.hint{text-align:center;font-size:12px;color:var(--text-faint);margin-top:10px;font-family:'JetBrains Mono',monospace;}
.sold-banner{display:none;align-items:center;gap:10px;background:var(--good-bg);border:1px solid #2f5c44;color:var(--good);font-weight:700;font-size:14px;padding:12px 14px;border-radius:12px;margin-bottom:14px;}
.sold-banner.show{display:flex;}
.pay-box{display:none;position:relative;background:var(--surface-2);border:1px solid var(--border);border-radius:12px;padding:14px 40px 16px 16px;margin-bottom:14px;}
.pay-box.show{display:block;}
.pay-title{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint);margin-bottom:8px;}
.pay-amount{font-size:14px;margin-bottom:10px;}
.pay-amount b{color:var(--gold);font-size:16px;}
.pay-list{margin:0 0 10px;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;}
.pay-list li{font-size:13px;color:var(--text-dim);background:var(--surface-3);border-radius:8px;padding:8px 10px;}
.pay-list b{color:var(--text);}
.pay-note{font-size:12px;color:var(--text-faint);line-height:1.5;}
.feed{margin-top:26px;}
.feed-title{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint);margin-bottom:10px;display:block;}
.feed-list{display:flex;flex-direction:column;gap:1px;background:var(--border);border-radius:12px;overflow:hidden;border:1px solid var(--border);}
.feed-row{display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--surface-2);padding:10px 13px;font-size:13px;}
.feed-amt{font-family:'JetBrains Mono',monospace;color:var(--gold);font-weight:700;}
.feed-time{font-family:'JetBrains Mono',monospace;color:var(--text-faint);font-size:11px;}
.feed-empty{padding:16px 13px;background:var(--surface-2);color:var(--text-faint);font-size:13px;text-align:center;}
.tiers{margin-top:18px;padding-top:16px;border-top:1px solid var(--border);display:flex;justify-content:space-between;gap:8px;}
.tier{flex:1;text-align:center;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-faint);}
.tier b{display:block;color:var(--text-dim);font-size:13px;}
.rules-box{margin-top:18px;padding-top:16px;border-top:1px solid var(--border);}
.rules-title{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint);margin-bottom:10px;}
.rules-list{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:7px;}
.rules-list li{font-size:13px;color:var(--text-dim);line-height:1.5;padding-left:16px;position:relative;}
.rules-list li::before{content:"\2014";position:absolute;left:0;color:var(--text-faint);}
.rules-list b{color:var(--text);}
.contact-line{margin-top:12px;font-size:12.5px;color:var(--text-faint);font-family:'JetBrains Mono',monospace;}
.contact-line a{color:var(--accent-2);text-decoration:none;}
.past-box{margin-top:22px;}
.past-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);font-size:12.5px;}
.past-result{font-family:'JetBrains Mono',monospace;color:var(--good);font-weight:700;}
.foot{text-align:center;font-size:12px;color:var(--text-faint);margin-top:18px;}
.foot a{color:var(--text-faint);}

/* pries-starto atgalinis skaiciavimas */
.countdown-overlay{
  position:absolute;inset:0;z-index:10;background:rgba(20,16,12,.97);
  border-radius:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;
}
.countdown-label{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.15em;text-transform:uppercase;color:var(--text-faint);}
.countdown-num{font-family:'Anton',sans-serif;font-size:120px;line-height:1;color:var(--gold);text-shadow:0 0 40px rgba(227,178,60,.5);animation:blink .9s ease-in-out;}
.countdown-num.start{
  color:#ff2b2b;text-shadow:0 0 50px rgba(255,43,43,.95),0 0 100px rgba(255,43,43,.6);
  font-size:110px;animation:startBlink 0.45s steps(1) 6;
}
@keyframes blink{0%{opacity:0;transform:scale(.6);}30%{opacity:1;transform:scale(1.08);}100%{opacity:1;transform:scale(1);}}
@keyframes startBlink{0%,100%{opacity:1;}50%{opacity:.15;}}
.countdown-sub{font-size:13px;color:var(--text-dim);text-align:center;padding:0 30px;}

/* svenciniai — kompaktiškas, neuždengia mygtukų */
.celebrate-overlay{
  position:fixed;inset:auto;top:14px;left:50%;transform:translateX(-50%);z-index:80;
  display:none;align-items:flex-start;justify-content:center;
  background:transparent;pointer-events:none;width:auto;max-width:min(280px,86vw);
}
.celebrate-overlay.show{display:flex;}
.celebrate-card{
  position:relative;pointer-events:auto;
  background:rgba(20,16,12,.96);border:2px solid var(--gold);border-radius:14px;
  padding:28px 14px 12px;text-align:center;width:100%;max-width:260px;
  box-shadow:0 12px 36px rgba(0,0,0,.55),0 0 24px rgba(227,178,60,.25);
}
.celebrate-hands{font-size:22px;margin-bottom:2px;animation:clap .35s ease-in-out infinite alternate;line-height:1;}
@keyframes clap{0%{transform:scale(1) rotate(-4deg);}100%{transform:scale(1.12) rotate(4deg);}}
.celebrate-persona{width:56px!important;height:56px!important;margin:0 auto 4px;display:block;object-fit:contain;}
.celebrate-emoji{font-size:22px;margin-bottom:4px;}
.celebrate-title{font-family:'Anton',sans-serif;font-size:18px;color:var(--gold);margin-bottom:2px;letter-spacing:.04em;}
.celebrate-sub{font-size:12px;color:var(--text-dim);line-height:1.35;}
.celebrate-sub b{color:var(--accent-2);}
.celebrate-close{margin-top:8px;background:var(--accent);color:#1a1006;border:none;padding:6px 14px;border-radius:8px;font-weight:700;font-size:12px;cursor:pointer;}
@media (max-width:640px){
  .celebrate-overlay{top:8px;max-width:min(220px,78vw);}
  .celebrate-card{padding:8px 10px 10px;max-width:200px;}
  .celebrate-persona{width:44px!important;height:44px!important;}
  .celebrate-title{font-size:15px;}
  .celebrate-hands{font-size:18px;}
}
#confettiCanvas{position:fixed;inset:0;z-index:49;pointer-events:none;display:none;}
#confettiCanvas.show{display:block;}

/* Vedėjas Vilkas — personažo atvaizdas */
.host-bar,#hostBar{display:none!important;visibility:hidden!important;height:0!important;max-height:0!important;margin:0!important;padding:0!important;border:0!important;overflow:hidden!important;opacity:0!important;pointer-events:none!important;}
@keyframes hostIdleGlow{0%,100%{filter:brightness(1);}50%{filter:brightness(1.08);}}
.host-wolf{display:none!important;}
.host-bubble{display:none!important;}
.host-wolf.idle{animation:wolfBob 1.8s ease-in-out infinite;}
.host-wolf.talking{animation:wolfTalk 0.45s ease-in-out infinite;}
.host-wolf.bow{animation:wolfBow 1.1s ease-in-out;}
.host-wolf.wave{animation:wolfWave 0.85s ease-in-out;}
@keyframes wolfBob{0%,100%{transform:translateY(0) rotate(0deg);}50%{transform:translateY(-6px) rotate(1.5deg);}}
@keyframes wolfTalk{0%,100%{transform:translateY(0) rotate(-1deg) scale(1);}50%{transform:translateY(-4px) rotate(2deg) scale(1.02);}}
@keyframes wolfBow{0%{transform:rotate(0deg) translateY(0);}35%{transform:rotate(12deg) translateY(10px);}55%{transform:rotate(14deg) translateY(12px);}100%{transform:rotate(0deg) translateY(0);}}
@keyframes wolfWave{0%,100%{transform:rotate(0deg) translateX(0);}25%{transform:rotate(-8deg) translateX(-6px);}50%{transform:rotate(10deg) translateX(8px);}75%{transform:rotate(-6deg) translateX(-4px);}}
.host-wolf-img{width:100%;height:100%;object-fit:contain;object-position:center bottom;display:block;filter:drop-shadow(0 10px 18px rgba(0,0,0,.6)) drop-shadow(0 0 16px rgba(255,140,40,.35));}
.cam-flash{position:fixed;z-index:61;width:var(--flash-size,clamp(160px,28vw,340px));height:var(--flash-size,clamp(160px,28vw,340px));transform:translate(-50%,-50%);border-radius:50%;pointer-events:none;background:radial-gradient(circle,#fff 0,rgba(255,255,255,.98) 16%,rgba(215,232,255,.75) 36%,rgba(255,255,255,0) 70%);mix-blend-mode:screen;opacity:0;animation:camFlash .7s ease-out forwards;}
.cam-flash::after{content:'';position:absolute;left:50%;top:50%;width:340%;height:6px;margin:-3px 0 0 -170%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.98),transparent);transform:rotate(var(--rot,20deg));}
@media (prefers-reduced-motion:reduce){.wolf-pop.show{transform:translateY(0);}.cam-flash{animation-duration:1s;filter:brightness(.6);}.cam-flash::after{display:none;}}
@keyframes camFlash{0%{opacity:0;transform:translate(-50%,-50%) scale(.4)}12%{opacity:1;transform:translate(-50%,-50%) scale(1.1)}100%{opacity:0;transform:translate(-50%,-50%) scale(1.4)}}
.wolf-pop.flash-hit .wolf-body img{filter:brightness(1.75) contrast(1.08);}
.wolf-photo{position:fixed;right:18px;bottom:225px;z-index:63;width:128px;padding:7px 7px 19px;background:#fff8e8;border:1px solid #e8d7ae;border-radius:3px;box-shadow:0 12px 34px rgba(0,0,0,.55);transform:translateY(30px) rotate(5deg) scale(.7);opacity:0;pointer-events:none;}
.wolf-photo.show{animation:wolfPhotoIn 8s cubic-bezier(.2,1.25,.3,1) forwards;}
.wolf-photo img{display:block;width:100%;height:112px;object-fit:contain;background:radial-gradient(circle,#5b2318,#160c09 72%);}
.wolf-photo span{display:block;color:#3b2518;font:700 10px/1.2 system-ui,sans-serif;text-align:center;margin-top:5px;letter-spacing:.02em;}
@keyframes wolfPhotoIn{0%{opacity:0;transform:translateY(30px) rotate(8deg) scale(.65)}12%,78%{opacity:1;transform:translateY(0) rotate(-3deg) scale(1)}100%{opacity:0;transform:translateY(-12px) rotate(-1deg) scale(.94)}}
@media(max-width:700px){.wolf-photo{right:6px;bottom:160px;width:92px;padding:5px 5px 14px}.wolf-photo img{height:78px}.wolf-photo span{font-size:8px}}
.wolf-pop{position:fixed;right:14px;left:auto;bottom:0;z-index:60;width:min(280px,26vw,40vh);max-width:calc(100vw - 28px);transform:translateY(110%);pointer-events:none;transition:none;overflow:visible;box-sizing:border-box;}
@media (min-width:1280px){
  .wolf-pop{width:min(240px,20vw,34vh);right:18px;}
}
.wolf-pop.show{animation:wolfPopIn .95s cubic-bezier(.22,1.55,.36,1) forwards;}
.wolf-pop.show.alive{animation:wolfPopIn .95s cubic-bezier(.22,1.55,.36,1) forwards, wolfStageSway 16s ease-in-out .95s infinite;}
/* −50% judesiai: duration ×2 + amplitudė /2 — be „traukulio“ */
.wolf-pop.has-video.show.alive{animation:wolfPopIn .95s cubic-bezier(.22,1.55,.36,1) forwards, wolfDiscoSway 12.4s ease-in-out .95s infinite;}
.wolf-pop.has-video .wolf-body{animation:wolfDiscoBob 7.6s ease-in-out infinite;}
.wolf-pop.has-video.idle .wolf-body{animation:wolfDiscoBob 7.6s ease-in-out infinite;}
.wolf-pop.has-video.talking .wolf-body{animation:wolfDiscoTalk 4.8s ease-in-out infinite;}
.wolf-pop.hide{animation:wolfPopOut .6s ease-in forwards;}
@keyframes wolfPopIn{
  0%{transform:translateY(110%) scale(.92,1.08) rotate(-4deg);}
  55%{transform:translateY(-4%) scale(1.04,.94) rotate(2deg);}
  72%{transform:translateY(2%) scale(.98,1.03) rotate(-1deg);}
  100%{transform:translateY(0) scale(1,1) rotate(0);}
}
@keyframes wolfPopOut{0%{transform:translateY(0);}100%{transform:translateY(112%);}}
@keyframes wolfStageSway{
  0%,100%{transform:translateY(0) rotate(-0.6deg) translateX(0);}
  25%{transform:translateY(-2.5px) rotate(0.8deg) translateX(0);}
  50%{transform:translateY(-1px) rotate(-0.5deg) translateX(-1px);}
  75%{transform:translateY(-3px) rotate(0.7deg) translateX(0);}
}
@keyframes wolfDiscoSway{
  0%,100%{transform:translateY(0) translateX(0) rotate(-0.7deg) scale(1,1);}
  20%{transform:translateY(-3px) translateX(0) rotate(0.9deg) scale(.9925,1.01);}
  40%{transform:translateY(-1px) translateX(-1px) rotate(-0.6deg) scale(1.0075,.9925);}
  60%{transform:translateY(-3.5px) translateX(0) rotate(0.75deg) scale(.995,1.0075);}
  80%{transform:translateY(-1.5px) translateX(-1.5px) rotate(-0.65deg) scale(1.005,.995);}
}
@keyframes wolfDiscoBob{
  0%,100%{transform:rotate(-0.6deg) translateY(0) translateX(0) scale(1,1);}
  25%{transform:rotate(0.8deg) translateY(-3px) translateX(0) scale(.99,1.015);}
  50%{transform:rotate(0.4deg) translateY(-1px) translateX(-1px) scale(1.01,.99);}
  75%{transform:rotate(-0.75deg) translateY(-2.5px) translateX(0) scale(.9925,1.01);}
}
@keyframes wolfDiscoTalk{
  0%,100%{transform:rotate(-0.75deg) translateY(0) translateX(0) scale(1,1);}
  33%{transform:rotate(1deg) translateY(-2.5px) translateX(0) scale(.985,1.02);}
  66%{transform:rotate(0.4deg) translateY(-1px) translateX(-1px) scale(1.015,.985);}
}
/* Tom-stilius: lėtas kvėpavimas — gyvas, be trūkčiojimo (−50%) */
.wolf-pop.idle .wolf-body{animation:wolfTomIdle 12.4s ease-in-out infinite;}
@keyframes wolfTomIdle{
  0%,100%{transform:rotate(-0.5deg) translateY(0) scale(1,1);}
  25%{transform:rotate(0.4deg) translateY(-2.5px) scale(.9925,1.0125);}
  50%{transform:rotate(0.6deg) translateY(-1px) scale(1.0075,.9925);}
  75%{transform:rotate(-0.4deg) translateY(-2px) scale(.995,1.0075);}
}
/* Be oranžinio „halo“ remo — tik lengvas šešėlis po kojom */
.wolf-pop img,.wolf-pop video{width:100%;display:block;transform-origin:50% 100%;background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none;filter:drop-shadow(-2px 10px 10px rgba(0,0,0,.4));}
/* Be remo / fono — tik vilkas (skaidrus anim WebP). */
.wolf-pop #wolfPopVid,.wolf-pop video{display:none;position:absolute;left:0;bottom:0;width:100%;max-height:100%;object-fit:contain;object-position:center bottom;pointer-events:none;background:transparent!important;border-radius:0!important;}
.wolf-pop.has-video #wolfPopImg,.wolf-pop.has-video #wolfPopGhost{opacity:0;visibility:hidden;}
.wolf-pop.has-video #wolfPopVid{opacity:1;display:block;}
/* LIP-SYNC: PC kalba → talking klasė (anim). Tyloje anim LIEKA matoma VISIEMS
   (telefonas niekada negauna talking iš TTS — seniau vid=0 + img fail → Vilkas DINGO). */
.wolf-pop.has-video #wolfPopVid,.wolf-pop.has-video #wolfPopImg{transition:opacity var(--wolf-fade-ms,220ms) ease;}
.wolf-pop.has-video:not(.talking) #wolfPopVid{opacity:1;}
.wolf-pop.has-video:not(.talking) #wolfPopImg{opacity:0;}
.wolf-pop.has-video.show #wolfPopVid{opacity:1;}
.wolf-pop.show:not(.has-video) #wolfPopImg{opacity:1;}
.wolf-pop .wolf-body{position:relative;transform-origin:50% 100%;will-change:transform;background:transparent!important;border:0!important;box-shadow:none!important;}
.wolf-pop.phone-ring .wolf-body{animation:phoneBuzz .12s linear infinite !important;}
@keyframes phoneBuzz{
  0%{transform:translate(0,0) rotate(0deg);}
  20%{transform:translate(-3px,2px) rotate(-1.5deg);}
  40%{transform:translate(3px,-2px) rotate(1.5deg);}
  60%{transform:translate(-2px,-1px) rotate(-1deg);}
  80%{transform:translate(2px,2px) rotate(1deg);}
  100%{transform:translate(0,0) rotate(0deg);}
}
.wolf-pop.talking .wolf-body{animation:wolfTomTalk 4.8s ease-in-out infinite;}
@keyframes wolfTomTalk{
  0%,100%{transform:rotate(-0.75deg) translateY(0) scale(1,1);}
  25%{transform:rotate(0.9deg) translateY(-2px) scale(.985,1.02);}
  50%{transform:rotate(0.4deg) translateY(-0.5px) scale(1.01,.99);}
  75%{transform:rotate(-0.9deg) translateY(-2.5px) scale(.99,1.015);}
}
.wolf-pop.strike img{animation:wolfStrike .35s cubic-bezier(.2,1.4,.4,1);}
@keyframes wolfStrike{0%{transform:scale(1.08,.9) translateY(-10px) rotate(-6deg);}35%{transform:scale(.92,1.1) translateY(6px) rotate(4deg);}100%{transform:scale(1) translateY(0) rotate(0);}}
.wolf-pop img.ghost{position:absolute;left:0;top:0;opacity:0;pointer-events:none;}
.wolf-pop img.ghost.fade{display:none;}
@keyframes ghostFade{0%{opacity:1;}100%{opacity:0;}}
.wolf-pop img.swap{animation:poseSwap .4s cubic-bezier(.25,1.5,.4,1);}
@keyframes poseSwap{0%{transform:rotate(-8deg) scale(.94,1.06) translateY(6px);}55%{transform:rotate(4deg) scale(1.05,.94) translateY(-4px);}100%{transform:rotate(0) scale(1) translateY(0);}}
.wolf-pop img.swap-up{animation:poseUp .45s cubic-bezier(.25,1.6,.4,1);}
@keyframes poseUp{0%{transform:scale(1.08,.88) translateY(8px);}40%{transform:scale(.94,1.1) translateY(-10px);}70%{transform:scale(1.04,.96) translateY(-2px);}100%{transform:scale(1,1) translateY(0);}}
.wolf-pop.talking.lean .wolf-body{animation:wolfTomLean 7.2s ease-in-out infinite;}
.wolf-pop.has-video.talking.lean .wolf-body{animation:wolfDiscoTalk 4.8s ease-in-out infinite;}
@keyframes wolfTomLean{
  0%,100%{transform:rotate(-1deg) translateY(0) scale(1,1);}
  30%{transform:rotate(1.1deg) translateY(-2px) scale(.99,1.015);}
  60%{transform:rotate(-0.7deg) translateY(-1px) scale(1.01,.99);}
}
.wolf-pop.coffee .wolf-body{animation:wolfSip 2.2s ease-in-out infinite;}
@keyframes wolfSip{0%,100%{transform:rotate(0) translateY(0);}25%{transform:rotate(-5deg) translateY(-4px);}50%{transform:rotate(-8deg) translateY(-2px) scale(1.02,.98);}75%{transform:rotate(-3deg) translateY(-5px);}}
.wolf-pop.surprise .wolf-body{animation:wolfSurprise .7s cubic-bezier(.2,1.5,.4,1);}
@keyframes wolfSurprise{0%{transform:scale(1) translateY(0);}30%{transform:scale(1.12,.85) translateY(-18px) rotate(-5deg);}55%{transform:scale(.9,1.12) translateY(4px) rotate(4deg);}100%{transform:scale(1) translateY(0) rotate(0);}}
@media (prefers-reduced-motion:reduce){
  .wolf-pop.idle .wolf-body,.wolf-pop.talking .wolf-body,.wolf-pop.show.alive,.wolf-pop.has-video .wolf-body,.wolf-pop.has-video.show.alive{animation:none!important;}

/* === VILKO_MOKYKLA_CSS === grakštumo parametrai — keičia smegenys.json per /api/vilkas/brain */
:root{--wolf-bob-px:4px;--wolf-sway-deg:1.2deg;--wolf-talk-s:4.8s;--wolf-walk-ms:900ms;--wolf-raise-px:10px;--wolf-fade-ms:220ms;--wolf-ease:cubic-bezier(.22,1,.36,1);--wolf-idle-s:4.2s;}
.wolf-pop.walk-in .wolf-body{animation:wolfWalkIn var(--wolf-walk-ms) var(--wolf-ease) both!important;}
@keyframes wolfWalkIn{0%{transform:translateX(30px) translateY(5px) rotate(2deg);opacity:.85;}35%{transform:translateX(16px) translateY(-3px) rotate(-1.2deg);opacity:1;}65%{transform:translateX(6px) translateY(2px) rotate(.8deg);}100%{transform:translateX(0) translateY(0) rotate(0);}}
.wolf-pop.raise-hand .wolf-body{animation:wolfRaiseHand .72s var(--wolf-ease) both!important;}
@keyframes wolfRaiseHand{0%{transform:translateY(0) rotate(0) scale(1);}38%{transform:translateY(calc(-1 * var(--wolf-raise-px))) rotate(-2deg) scale(1.02);}68%{transform:translateY(calc(-.55 * var(--wolf-raise-px))) rotate(1deg) scale(1.01);}100%{transform:translateY(0) rotate(0) scale(1);}}
.wolf-pop.soft-sway .wolf-body{animation:wolfSoftSway var(--wolf-idle-s) ease-in-out infinite!important;}
@keyframes wolfSoftSway{0%,100%{transform:translateY(0) rotate(0);}50%{transform:translateY(calc(-1 * var(--wolf-bob-px))) rotate(var(--wolf-sway-deg));}}
.wolf-pop .wolf-body{transition:filter var(--wolf-fade-ms) ease;}
}
.fx-float{position:fixed;z-index:61;pointer-events:none;will-change:transform,opacity;line-height:1;}
.fx-bigheart{left:50%;top:42%;font-size:min(20vh,150px);transform:translate(-50%,-50%) scale(0);animation:bigHeart 1.9s cubic-bezier(.2,1.4,.4,1) forwards;filter:drop-shadow(0 0 30px rgba(255,40,90,.8));}
@keyframes bigHeart{0%{transform:translate(-50%,-50%) scale(0) rotate(-20deg);opacity:0;}20%{transform:translate(-50%,-50%) scale(1.15) rotate(6deg);opacity:1;}32%{transform:translate(-50%,-50%) scale(.92);}44%{transform:translate(-50%,-50%) scale(1.1);}56%{transform:translate(-50%,-50%) scale(.98);}80%{transform:translate(-50%,-60%) scale(1);opacity:1;}100%{transform:translate(-50%,-120%) scale(.6);opacity:0;}}
.fx-mini{font-size:28px;animation:miniFly 1.6s ease-out forwards;}
@keyframes miniFly{0%{transform:translate(0,0) scale(.4);opacity:0;}15%{opacity:1;}100%{transform:translate(var(--dx),var(--dy)) scale(1.2) rotate(var(--rot));opacity:0;}}
#smokeField{position:fixed;inset:0;z-index:55;pointer-events:none;overflow:hidden;opacity:0;transition:opacity .45s ease;}
#smokeField{display:none!important;}
#smokeField.on{opacity:1;}
#smokeField .smoke-cloud{
  position:absolute;right:2%;bottom:0;width:min(420px,48vw);height:min(380px,52vh);
  background:
    radial-gradient(ellipse 70% 55% at 55% 78%, rgba(255,255,255,.92), rgba(255,255,255,.55) 40%, transparent 72%),
    radial-gradient(ellipse 55% 45% at 30% 70%, rgba(255,255,255,.85), transparent 68%),
    radial-gradient(ellipse 50% 40% at 75% 60%, rgba(255,255,255,.78), transparent 65%);
  filter:blur(6px);opacity:.95;animation:smokeCloudPulse 4.5s ease-in-out infinite;
}
@keyframes smokeCloudPulse{
  0%,100%{transform:scale(1) translateY(0);opacity:.88;}
  50%{transform:scale(1.08) translateY(-18px);opacity:1;}
}
.smoke-puff{
  position:absolute;width:var(--sz,180px);height:var(--sz,180px);border-radius:50%;
  background:
    radial-gradient(circle at 40% 40%, rgba(255,255,255,.98), rgba(255,255,255,.7) 38%, rgba(255,255,255,.25) 62%, transparent 78%);
  filter:blur(4px);opacity:0;
  animation:smokeDrift var(--dur,7s) ease-out forwards;
  box-shadow:0 0 40px rgba(255,255,255,.55);
}
@keyframes smokeDrift{
  0%{opacity:0;transform:translate(0,40px) scale(.4);}
  10%{opacity:.95;}
  40%{opacity:1;transform:translate(var(--sx,20px),-80px) scale(1.15);}
  70%{opacity:.75;transform:translate(calc(var(--sx,20px)*1.2),-160px) scale(1.35);}
  100%{opacity:0;transform:translate(calc(var(--sx,20px)*1.4),-240px) scale(1.55);}
}
@media (prefers-reduced-motion:reduce){
  #smokeField .smoke-cloud{animation:none;}
  .smoke-puff{animation-duration:1s!important;}
}
.wolf-pop-bubble{position:absolute;right:0;left:auto;bottom:94%;transform:scale(0.75);transform-origin:100% 100%;width:max-content;min-width:200px;max-width:min(400px,30vw);background:rgba(14,11,20,.86);backdrop-filter:blur(8px);color:#f2e8d8;font-family:system-ui,'Segoe UI',Arial,sans-serif;font-size:15px;letter-spacing:0;line-height:1.45;text-align:left;padding:10px 14px;border-radius:12px;border:1px solid rgba(255,190,110,.35);box-shadow:0 10px 30px rgba(0,0,0,.45);opacity:0;pointer-events:none;transition:opacity .2s ease;}
.wolf-pop-bubble::after{content:'';position:absolute;left:auto;right:22%;top:100%;border:9px solid transparent;border-top-color:rgba(14,11,20,.86);transform:none;}
.wolf-pop.show .wolf-pop-bubble{opacity:0;pointer-events:none;}
.wolf-pop.show .wolf-pop-bubble.open{opacity:1;pointer-events:auto;transform:scale(0.75);}
.wolf-pop-bubble.pop{animation:bubbleIn .25s ease-out;}
.wolf-pop-bubble:empty,.wolf-pop-bubble.blank{display:none;}
.wolf-pop-bubble .bt{display:block;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#ffb35c;margin-bottom:4px;}
.wolf-pop-bubble .bt:empty{display:none;}
.wolf-pop-bubble .bs{display:block;font-size:15px;font-weight:500;letter-spacing:0;line-height:1.45;color:#f2e8d8;}
.wolf-pop-bubble .bs:empty{display:none;}
.wolf-pop-bubble .bs span{opacity:0;display:inline-block;transition:opacity .14s ease;margin-right:4px;}
.wolf-pop-bubble .bs span.on{opacity:1;}
.wolf-pop-bubble.noaudio .bs span{opacity:1;}
.wolf-pop-bubble{display:none!important;}
.voice-unlock{position:fixed;left:50%;top:18px;transform:translateX(-50%);z-index:90;background:#dc2626;color:#fff;border:0;border-radius:999px;padding:12px 22px;font:700 17px system-ui,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.5);cursor:pointer;display:none;animation:redPulse 1.2s infinite;}
.voice-unlock.show{display:block;}
#discoField{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;opacity:0;transition:opacity .5s ease;}
#discoField.on{opacity:1;}
body:not(.cover-mode) #discoField{opacity:0!important;visibility:hidden;}
/* antraštė / UI virš diskotekos — kaip buvo */
body.cover-mode{padding-top:8px;}
body.cover-mode .brand{z-index:6;isolation:isolate;}
.disco-bg{
  position:absolute;inset:0;
  background:
    radial-gradient(60vmax 44vmax at 50% 108%, hsla(var(--dh,212),100%,60%,.50), transparent 62%),
    radial-gradient(46vmax 34vmax at 12% -6%, hsla(var(--dhA,192),100%,55%,.38), transparent 60%),
    radial-gradient(46vmax 34vmax at 88% -6%, hsla(var(--dhB,232),100%,64%,.42), transparent 60%),
    radial-gradient(30vmax 22vmax at 50% 42%, hsla(var(--dh,212),100%,75%,.20), transparent 65%),
    linear-gradient(180deg,#04040c 0%,#060a24 55%,#03030a 100%);
}
/* ryškūs klubiniai spotai / spinduliai / strobe — kaip video fone (mėlyna/neonas) */
.disco-spot,.disco-beam,.disco-strobe{display:block!important;}
#discoField.beat .disco-bg{filter:brightness(1.28) saturate(1.35);}
#discoField.beat .disco-dancer .dd-spin{filter:brightness(1.14) saturate(1.2);}
.disco-spot{
  position:absolute;width:44vmax;height:44vmax;border-radius:50%;
  filter:blur(26px);mix-blend-mode:screen;opacity:.75;
  transform:translate(-50%,-50%);
  transition:background .08s linear, opacity .1s linear;
}
.disco-spot.s1{left:18%;top:28%;background:rgba(0,180,255,.65);}
.disco-spot.s2{left:82%;top:22%;background:rgba(90,80,255,.65);}
.disco-spot.s3{left:50%;top:70%;background:rgba(0,120,255,.60);}
.disco-spot.s4{left:30%;top:75%;background:rgba(0,255,240,.45);}
.disco-spot.s5{left:70%;top:60%;background:rgba(150,220,255,.50);}
.disco-beam{
  position:absolute;top:-10%;width:10px;height:120%;
  background:linear-gradient(180deg,rgba(200,235,255,.85),rgba(80,160,255,.15) 60%,rgba(255,255,255,0));
  filter:blur(1px);opacity:.55;transform-origin:50% 0%;
  mix-blend-mode:screen;
}
.disco-beam.b1{left:22%;transform:rotate(12deg);}
.disco-beam.b2{left:48%;transform:rotate(-6deg);}
.disco-beam.b3{left:74%;transform:rotate(8deg);}
.disco-floor{
  position:absolute;left:0;right:0;bottom:0;height:42%;
  background:
    repeating-linear-gradient(90deg,rgba(255,255,255,.04) 0 2px,transparent 2px 48px),
    repeating-linear-gradient(0deg,rgba(255,255,255,.03) 0 2px,transparent 2px 48px),
    linear-gradient(180deg,transparent,rgba(0,0,0,.65));
  opacity:.55;transform:perspective(400px) rotateX(58deg);transform-origin:50% 100%;
}
.disco-strobe{
  position:absolute;inset:0;background:#fff;opacity:0;mix-blend-mode:overlay;
  pointer-events:none;
}
#discoField.beat .disco-strobe{animation:discoFlash .16s ease-out;}
#discoField.beat .disco-bg{filter:brightness(1.28) saturate(1.35);}
@keyframes discoFlash{0%{opacity:.14;}100%{opacity:0;}}
/* Klubinė siena: šokėja PRIGLAUSTA prie kairio rėmelio (be tarpo), nuo VAKARE apačios iki pat apačios */
.disco-dancers{position:absolute;left:0;right:0;top:16%;bottom:0;height:auto;z-index:3;pointer-events:none;
  display:flex;align-items:stretch;justify-content:flex-start;gap:min(2vw,22px);
  padding:0 12px 0 200px;}
.disco-dancer{position:relative;flex:0 1 min(340px,26vw);height:min(260px,38vh);transform:none;opacity:.94;}
.disco-dancer.dv2{flex:1 1 auto;max-width:none;height:100%;min-height:0;opacity:1;z-index:4;
  filter:drop-shadow(0 0 44px rgba(60,160,255,.45));}
.disco-dancer.dv2 .dd-spin{border-color:rgba(140,210,255,.9);
  box-shadow:0 0 0 1px rgba(0,0,0,.6),0 18px 44px rgba(0,0,0,.75),0 0 54px rgba(40,150,255,.55),0 0 110px rgba(0,220,255,.35);}
.dd-spin{width:100%;height:100%;transform-origin:50% 100%;will-change:transform;overflow:hidden;border-radius:16px;
  border:2px solid rgba(255,200,90,.55);
  box-shadow:0 0 0 1px rgba(0,0,0,.6),0 14px 34px rgba(0,0,0,.7),0 0 26px rgba(255,150,40,.30),0 0 60px rgba(200,40,255,.22);
  filter:saturate(1.25) contrast(1.1) brightness(1.06);
  transition:opacity .6s ease;position:relative;}
/* Kontaktai — šokėjų lango viršus dešinėje (virš video, paspaudžiami) */
.disco-contacts{
  position:absolute;top:10px;right:12px;z-index:20;
  display:flex;flex-direction:column;align-items:flex-end;gap:4px;
  pointer-events:auto!important;max-width:min(300px,52%);
  font-family:'Archivo',sans-serif;font-size:11px;line-height:1.3;
  color:rgba(243,232,211,.95);text-align:right;
  text-shadow:0 1px 4px rgba(0,0,0,.95),0 0 10px rgba(0,0,0,.6);
}
.disco-contacts a.disco-contact-a{
  color:#7dffa8;text-decoration:none;word-break:break-word;cursor:pointer;
  pointer-events:auto!important;padding:6px 8px;margin:-2px 0;
  display:inline-block;border-radius:6px;background:rgba(0,0,0,.28);
  -webkit-tap-highlight-color:rgba(125,255,168,.25);touch-action:manipulation;
  font-size:12px;line-height:1.35;max-width:100%;
}
.disco-contacts a.disco-contact-a:hover,
.disco-contacts a.disco-contact-a:active{text-decoration:underline;filter:brightness(1.18);background:rgba(0,0,0,.42);}
#contactToast{
  position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;
  background:rgba(12,14,20,.92);color:#f3e8d3;border:1px solid rgba(125,255,168,.45);
  padding:10px 16px;border-radius:10px;font:600 13px/1.35 Archivo,sans-serif;
  box-shadow:0 10px 28px rgba(0,0,0,.45);opacity:0;pointer-events:none;transition:opacity .2s ease;
  max-width:min(92vw,420px);text-align:center;
}
#contactToast.show{opacity:1;}
.dd-video{width:100%;height:100%;object-fit:cover;object-position:center 35%;display:block;background:#000;position:relative;z-index:1;pointer-events:none;}
.dd-photo{display:none!important;}
.dd-arms,.dd-arm,.dd-legs-wrap{display:none!important;}
@media (max-width:899px){
  .disco-dancers{top:auto;height:44%;gap:8px;padding:0 8px;justify-content:center;}
  .disco-dancer{flex-basis:31vw;height:30vh;}
  .disco-dancer.dv2{height:44vh;flex:1 1 auto;max-width:none;}
}
@media (prefers-reduced-motion:reduce){
  /* Transliacija VIENA visiems — šokėjų NEslepiam (telefonas su Reduce Motion vis tiek mato įžangą) */
}
.vilkas-stage-btn{display:none!important;} /* įžangoje ir scenoje — tik F9/F10 */
body.cover-mode .wolf-pop,
body.cover-mode .wolf-photo,
body.cover-mode .wolf-impact,
body.cover-mode .showcase,
body.cover-mode .celebrate-overlay{display:none!important;}
body.cover-mode #mainPanel{display:none!important;}
body.cover-mode .voice-unlock{display:none!important;}
body.cover-mode .queue-rail{display:none!important;} /* prekių navigacija — tik po F9 */
body.cover-mode .qr-modal{display:none!important;}
@keyframes bubbleIn{0%{transform:scale(.64);}70%{transform:scale(.78);}100%{transform:scale(.75);}}
.wolf-impact{position:fixed;inset:0;z-index:59;pointer-events:none;background:radial-gradient(circle at 86% 85%,rgba(255,220,120,.55),rgba(255,120,0,0) 45%);opacity:0;}
.wolf-impact.go{animation:impactFlash .35s ease-out;}
@keyframes impactFlash{0%{opacity:1;}100%{opacity:0;}}
.stage.shake{animation:screenShake .3s ease-out;}
@keyframes screenShake{0%,100%{transform:translate(0,0);}20%{transform:translate(-7px,4px);}40%{transform:translate(6px,-5px);}60%{transform:translate(-4px,3px);}80%{transform:translate(3px,-2px);}}
@media (max-width:640px){.wolf-pop{width:min(170px,38vw);}.wolf-pop-bubble{font-size:13px;min-width:150px;max-width:70vw;}.wolf-pop-bubble .bt{font-size:11px;}.wolf-pop-bubble .bs{font-size:13px;}}
.host-info{flex:1;min-width:0;}
.host-name{font-family:'Anton',sans-serif;font-size:22px;line-height:1.2;color:#ffb347;letter-spacing:.03em;margin:0 0 6px;text-shadow:0 0 14px rgba(255,160,40,.5);}
.host-name .host-time{
  display:inline-block;margin-left:6px;padding:2px 10px 3px;border-radius:8px;
  font-family:'JetBrains Mono',monospace;font-size:1.05em;font-weight:700;letter-spacing:.06em;
  color:#0a0a0a;background:linear-gradient(180deg,#7dff9a,#39ff6a 55%,#1ecf4a);
  box-shadow:0 0 18px rgba(57,255,106,.75),0 0 4px rgba(125,255,154,.9),inset 0 1px 0 rgba(255,255,255,.45);
  text-shadow:none;vertical-align:baseline;
}
.host-bubble{background:linear-gradient(180deg,rgba(255,200,100,.14),rgba(255,255,255,.06));border:1px solid rgba(255,180,80,.45);border-radius:14px;padding:12px 14px;font-size:15px;line-height:1.45;color:#fff4e4;min-height:52px;transition:transform .2s ease,box-shadow .2s ease;}
.host-bubble.talk{animation:bubblePop .45s ease;box-shadow:0 0 18px rgba(255,120,40,.35);}
@keyframes bubblePop{0%{transform:scale(.94);}50%{transform:scale(1.03);}100%{transform:scale(1);}}
.host-bubble b{color:#ff9a4a;}
.host-controls{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;}
.host-btn{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.06em;text-transform:uppercase;background:rgba(255,122,51,.15);border:1px solid rgba(255,122,51,.4);color:#ffb347;padding:6px 10px;border-radius:999px;cursor:pointer;}
.host-btn.on{background:rgba(76,175,125,.2);border-color:rgba(76,175,125,.55);color:#7dffa8;}
.host-flash{animation:hostFlash .55s ease;}
@keyframes hostFlash{0%,100%{box-shadow:0 14px 32px -14px rgba(255,60,0,.5);}40%{box-shadow:0 0 40px rgba(255,80,0,.95),0 0 14px rgba(255,200,60,.55);}}
.celebrate-persona{width:120px;height:120px;object-fit:cover;border-radius:16px;margin:0 auto 10px;display:block;border:2px solid rgba(255,180,60,.6);box-shadow:0 8px 24px rgba(0,0,0,.45);}
@media (max-width:640px){
  .host-wolf{width:140px;height:160px;}
  .host-name{font-size:16px;}
  .host-bubble{font-size:13px;padding:10px 12px;}
}
.bid-btn{position:relative;overflow:hidden;font-family:'Anton',sans-serif;font-size:24px;letter-spacing:.04em;text-transform:uppercase;color:#fff;background:radial-gradient(circle at 50% 30%,#ff5a4a,#d4121e 60%,#8e0a12);border:3px solid #ffcf5a;padding:20px 16px;border-radius:999px;text-shadow:0 2px 0 rgba(0,0,0,.35);box-shadow:0 0 0 4px rgba(255,40,40,.25),0 10px 30px -6px rgba(255,30,30,.8),inset 0 -6px 0 rgba(0,0,0,.25);}
.bid-btn:not(:disabled){animation:redPulse 1.2s ease-in-out infinite;}
.bid-btn:not(:disabled):hover{filter:brightness(1.12);}
.bid-btn:not(:disabled):active{transform:scale(.96) translateY(2px);}
.bid-btn:disabled{opacity:.8;filter:saturate(.75);}
.bid-btn .step{color:#fff;background:rgba(0,0,0,.28);font-size:15px;}
@keyframes redPulse{0%,100%{box-shadow:0 0 0 4px rgba(255,40,40,.25),0 10px 30px -6px rgba(255,30,30,.8),inset 0 -6px 0 rgba(0,0,0,.25);}50%{box-shadow:0 0 0 12px rgba(255,40,40,.12),0 12px 44px -4px rgba(255,40,40,1),inset 0 -6px 0 rgba(0,0,0,.25);}}
.bid-btn.armed{animation:redPulse .8s ease-in-out infinite !important;opacity:1 !important;filter:none !important;}
.bid-btn.go-green{background:radial-gradient(circle at 50% 30%,#6dff8f,#12b83a 60%,#0a6b22) !important;border-color:#eaffb0;animation:greenPulse 1s ease-in-out infinite !important;opacity:1 !important;filter:none !important;font-size:44px;padding:8px 16px;}
@keyframes greenPulse{0%{transform:scale(1);box-shadow:0 0 0 4px rgba(40,255,90,.3),0 10px 30px -6px rgba(30,255,80,.8);}15%{transform:scale(1.07);}40%{transform:scale(1);box-shadow:0 0 0 16px rgba(40,255,90,.08),0 12px 44px -4px rgba(40,255,90,1);}100%{transform:scale(1);}}
.bid-btn.start-pop{animation:startPop .9s cubic-bezier(.2,1.8,.4,1) !important;font-size:46px;padding:8px 16px;opacity:1 !important;filter:none !important;}
@keyframes startPop{0%{transform:scale(.4) rotate(-8deg);}45%{transform:scale(1.25) rotate(3deg);}70%{transform:scale(.95);}100%{transform:scale(1);}}
.bid-btn .bid-time{font-family:'JetBrains Mono',monospace;font-size:20px;background:rgba(0,0,0,.35);color:#fff;padding:4px 12px;border-radius:999px;margin-left:6px;}
.bid-btn .bid-time:empty{display:none;}
.bid-btn.hurry .bid-time{background:#fff;color:#d4121e;animation:hurryBlink .5s steps(2) infinite;}
@keyframes hurryBlink{50%{opacity:.35;}}
.showcase{display:none !important;position:fixed;z-index:58;left:36%;top:48%;width:min(560px,48vw);transform:translate(-50%,-50%) scale(0);background:#fffaf0;color:#2a1508;border:4px solid #ffb347;border-radius:22px;padding:12px;box-shadow:0 20px 60px rgba(0,0,0,.6),0 0 40px rgba(255,160,40,.45);pointer-events:none;opacity:0;}
.showcase.show{animation:showIn .6s cubic-bezier(.2,1.5,.4,1) forwards;}
.showcase.hide{animation:showOut .4s ease-in forwards;}
@keyframes showIn{0%{transform:translate(-120%,20%) scale(.2) rotate(-12deg);opacity:0;}100%{transform:translate(-50%,-50%) scale(1) rotate(0);opacity:1;}}
@keyframes showOut{0%{transform:translate(-50%,-50%) scale(1);opacity:1;}100%{transform:translate(-50%,-50%) scale(.3);opacity:0;}}
.showcase img{width:100%;max-height:46vh;object-fit:contain;object-position:left center;border-radius:14px;background:#f1e6d2;display:block;}
.showcase h3{font-family:'Anton',sans-serif;font-size:24px;margin:10px 4px 6px;letter-spacing:.02em;}
.showcase .chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 2px;}
.showcase .chip{font-size:13px;font-weight:700;padding:4px 9px;border-radius:999px;opacity:0;animation:chipIn .35s ease-out forwards;}
.chip.plus{background:#d8f7df;color:#11622a;}.chip.def{background:#ffe1d1;color:#9a3510;}.chip.inc{background:#dde8ff;color:#1f3d8a;}.chip.price{background:#d4121e;color:#fff;font-size:16px;}
@keyframes chipIn{0%{opacity:0;transform:translateY(8px) scale(.8);}100%{opacity:1;transform:none;}}
.wolf-table{position:fixed;z-index:61;bottom:0;left:auto;right:calc(min(280px,26vw,40vh) + 12px);width:min(170px,20vw);transform:translateX(60%);opacity:0;pointer-events:none;filter:drop-shadow(0 14px 22px rgba(0,0,0,.6));}
.wolf-table.show{animation:tableIn .8s cubic-bezier(.2,1.2,.4,1) forwards;}
.wolf-table.hide{animation:tableOut .5s ease-in forwards;}
@keyframes tableIn{0%{transform:translateX(60%);opacity:0;}100%{transform:translateX(0);opacity:1;}}
@keyframes tableOut{0%{transform:translateX(0);opacity:1;}100%{transform:translateX(70%);opacity:0;}}
@media (max-width:760px){.showcase{left:50%;top:32%;width:84vw;}.showcase img{max-height:26vh;}.wolf-table{right:calc(min(170px,38vw) + 4px);width:min(110px,22vw);}}
.past-box{display:none!important;}
.wait-box,.wait-text,.art-empty{display:none!important;}
.wait-box .bid-btn{max-width:420px;}
.bid-btn::after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.25),transparent);transform:translateX(-120%);pointer-events:none;}
.bid-btn:not(:disabled):active::after{animation:bidShine .45s ease;}
@keyframes bidShine{to{transform:translateX(120%);}}
/* ——— Šio vakaro prekių eilė (apačia) — kompaktiška ~70–80px ——— */
.queue-rail{
  position:fixed;left:50%;bottom:0;transform:translateX(-50%);z-index:66;
  width:min(520px,calc(100vw - 16px));
  background:linear-gradient(180deg,rgba(10,10,10,.92),#0a0a0a 40%);
  border:1px solid rgba(255,180,80,.28);border-bottom:none;
  border-radius:8px 8px 0 0;padding:3px 5px 4px;
  box-shadow:0 -6px 22px rgba(0,0,0,.5);backdrop-filter:blur(8px);
}
.queue-rail.qr-empty{opacity:.55;}
.qr-head{display:flex;align-items:baseline;justify-content:space-between;gap:4px;margin:0 2px 2px;padding:0 1px;}
.qr-title{font-family:'Anton',sans-serif;font-size:9px;letter-spacing:.05em;text-transform:uppercase;color:#ffb347;line-height:1.1;}
.qr-sub{font-size:7px;letter-spacing:.04em;color:rgba(243,232,211,.55);}
.qr-row{display:flex;align-items:center;gap:4px;}
.qr-arrow{
  flex:0 0 20px;height:42px;border:1px solid rgba(255,180,80,.4);border-radius:6px;
  background:rgba(255,255,255,.04);color:#ffb347;font-size:17px;line-height:1;cursor:pointer;
  display:flex;align-items:center;justify-content:center;padding:0;
}
.qr-arrow:hover{background:rgba(255,180,80,.15);color:#fff;}
.qr-arrow:disabled{opacity:.25;cursor:default;}
.qr-viewport{flex:1 1 auto;overflow:hidden;mask-image:linear-gradient(90deg,transparent,#000 10px,#000 calc(100% - 10px),transparent);}
.qr-track{display:flex;gap:0;width:max-content;will-change:transform;margin:0;padding:0;}
.qr-card{
  flex:0 0 68px;width:68px;background:#14100c;border:1px solid rgba(255,180,80,.25);
  border-radius:0;overflow:hidden;cursor:pointer;text-align:left;padding:0;margin:0;color:inherit;
  font:inherit;transition:border-color .2s,box-shadow .2s;
}
/* Gretimi remeliai lieciasi — antras border sutampa su pirmu (collapse) */
.qr-card + .qr-card{margin-left:-1px;}
.qr-card:first-child{border-radius:7px 0 0 7px;}
.qr-card:last-child{border-radius:0 7px 7px 0;}
.qr-card:only-child{border-radius:7px;}
.qr-card:hover{border-color:#39ff6a;z-index:1;box-shadow:0 4px 12px rgba(0,0,0,.4);}
.qr-card.now{border-color:#39ff6a;z-index:2;box-shadow:0 0 0 1px rgba(57,255,106,.35);}
.qr-photo{height:30px;margin:0;padding:0;background:#1a1510;display:flex;align-items:center;justify-content:center;overflow:hidden;}
.qr-photo img{width:100%;height:100%;object-fit:cover;object-position:left center;display:block;margin:0;padding:0;border:0;}
.qr-photo .ph{font-size:7px;color:rgba(243,232,211,.35);}
.qr-meta{padding:2px 3px 3px;}
.qr-ord{display:inline-block;font-size:7px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  color:#0a0a0a;background:#39ff6a;border-radius:2px;padding:0 3px;margin-bottom:1px;}
.qr-card:not(.now) .qr-ord{background:#ffb347;}
.qr-name{font-size:7px;font-weight:600;line-height:1.15;color:#f3ead9;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden;min-height:1.15em;}
.qr-price{margin-top:1px;font-family:'Anton',sans-serif;font-size:9px;color:#e3b23c;letter-spacing:.02em;}
.qr-price small{font-size:7px;font-family:'Archivo',sans-serif;color:rgba(243,232,211,.5);font-weight:500;margin-left:1px;}
.qr-def{display:none!important;}
.qr-def:empty{display:none;}
.qr-modal{position:fixed;inset:0;z-index:95;display:none;align-items:center;justify-content:center;
  background:rgba(0,0,0,.72);padding:16px;backdrop-filter:blur(4px);}
.qr-modal.open{display:flex;}
.qr-modal-card{width:min(440px,96vw);max-height:90vh;overflow:auto;background:#1a1510;
  border:1px solid rgba(255,180,80,.4);border-radius:16px;padding:14px;box-shadow:0 20px 60px rgba(0,0,0,.6);position:relative;}
.qr-modal-close{position:absolute;top:8px;right:10px;border:0;background:rgba(255,255,255,.08);color:#fff;
  width:34px;height:34px;border-radius:50%;font-size:20px;cursor:pointer;line-height:1;}
.qr-modal-img{width:100%;max-height:48vh;object-fit:contain;object-position:left center;background:#0a0a0a;border-radius:12px;display:block;}
.qr-modal-ord{display:inline-block;margin:10px 0 6px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:#0a0a0a;background:#39ff6a;border-radius:4px;padding:2px 8px;}
.qr-modal-title{font-family:'Anton',sans-serif;font-size:22px;letter-spacing:.02em;margin:0 0 8px;line-height:1.15;}
.qr-modal-price{font-size:18px;color:#e3b23c;font-weight:700;margin:0 0 10px;}
.qr-modal-row{font-size:13px;line-height:1.45;color:rgba(243,232,211,.85);margin:0 0 8px;}
.qr-modal-row b{color:#ffb347;font-weight:600;}
@media (max-width:720px){
  .queue-rail{width:calc(100vw - 8px);padding:2px 3px 3px;}
  .qr-card{flex-basis:64px;width:64px;}
  .qr-photo{height:28px;}
  .qr-arrow{flex-basis:18px;height:38px;font-size:15px;}
  .qr-title{font-size:8px;}
  body{padding-bottom:100px;}
  .item-body{padding-bottom:78px;}
  .art img{max-height:225px;}
}
</style></head>
<body class="__BODY_CLASS__">
<canvas id="confettiCanvas"></canvas>
<div id="smokeField" aria-hidden="true"><div class="smoke-cloud"></div></div>
<div id="discoField" class="__DISCO_CLASS__" aria-hidden="true">
  <div class="disco-bg"></div>
  <div class="disco-spot s1"></div>
  <div class="disco-spot s2"></div>
  <div class="disco-spot s3"></div>
  <div class="disco-spot s4"></div>
  <div class="disco-spot s5"></div>
  <div class="disco-beam b1"></div>
  <div class="disco-beam b2"></div>
  <div class="disco-beam b3"></div>
  <div class="disco-floor"></div>
  <div class="disco-dancers">
    <div class="disco-dancer dv2"><div class="dd-spin">
      <video class="dd-video" src="/photos/dance_club_2.mp4" autoplay muted loop playsinline preload="auto" aria-hidden="true"></video>
      <div id="dancerCount" style="position:absolute;right:8px;bottom:6px;z-index:5;pointer-events:none;font-size:12px;font-weight:700;color:#f5c542;text-shadow:0 1px 3px #000;opacity:.9;">1/15</div>
      <div class="disco-contacts" id="discoContacts">
        <a id="discoMailLink" class="disco-contact-a" href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=mindaugasbusiness@gmail.com&amp;su=Penktadienio%20aukcionas" target="_blank" rel="noopener">Kontaktai: mindaugasbusiness@gmail.com</a>
        <a id="discoTelLink" class="disco-contact-a" href="tel:+37066331913" data-phone="+37066331913">Tel. pasiteiravimui: +370&nbsp;663&nbsp;31913</a>
      </div>
    </div></div>
  </div>
  <div class="disco-strobe"></div>
</div>
<div id="contactToast" role="status" aria-live="polite"></div>
<div class="pay-strip" id="payStrip">
  <div class="auction-quick-rules" id="aqrPanel">
    <button type="button" class="ui-close-x" id="aqrClose" aria-label="Uždaryti">✕</button>
    <div class="aqr-title">Kaip veikia šis aukcionas</div>
    <ul>
      <li>Prieš siūlant kainą būtina užsiregistruoti.</li>
      <li>Vilkas pristato prekę, tada mygtukas skaičiuoja 9…1 — START!</li>
      <li>Kiekvienas pasiūlymas pratęsia laikmatį iki 1:00.</li>
      <li>Paskutinis pasiūlęs, kai laikas baigiasi — laimi.</li>
      <li>Siuntimas nurodytas prie daikto ir apmokamas atskirai.</li>
    </ul>
    <div class="aqr-contact">
      Kontaktai: <a href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=mindaugasbusiness@gmail.com&amp;su=Penktadienio%20aukcionas" target="_blank" rel="noopener">mindaugasbusiness@gmail.com</a><br>
      Tel. pasiteiravimui: <a href="tel:+37066331913" data-phone="+37066331913">+370&nbsp;663&nbsp;31913</a>
    </div>
  </div>
  <div class="pay-strip-title">Atsiskaitymas už laimėtą prekę</div>
  <div class="pay-row">
    <div class="pay-badges">
      <button type="button" class="pay-badge paypal" data-pay="paypal">PayPal</button>
      <button type="button" class="pay-badge skrill" data-pay="skrill">Skrill</button>
      <button type="button" class="pay-badge neteller" data-pay="neteller">Neteller</button>
      <button type="button" class="pay-badge paysafe" data-pay="paysafe">Paysafe</button>
    </div>
  </div>
  <button type="button" class="aqr-toggle" id="aqrToggle">ℹ Taisyklės · tel.</button>
  <div class="pay-strip-detail" id="payStripDetail">
    <button type="button" class="ui-close-x" id="payStripDetailClose" aria-label="Uždaryti">✕</button>
    <div class="psd-name" id="psdName"></div>
    <p class="psd-hint" id="psdHint"></p>
  </div>
</div>
<div class="participants-panel" id="participantsPanel" aria-label="Dalyviai">
  <div class="pp-count" id="ppCount">0 dalyvių</div>
  <div class="pp-label">Užsiregistravę</div>
  <div class="pp-list" id="ppList"><div class="pp-empty">Kol kas nieko</div></div>
  <div class="pp-reg" id="joinForm">
    <div class="pp-reg-title" id="joinFormTitle">1. Registracija</div>
    <input type="text" id="nameInput" placeholder="Vardas ir pavardė (privatu)" maxlength="80" autocomplete="name" title="Vardas ir pavardė (privatu)">
    <input type="text" id="nicknameInput" placeholder="Slapyvardis (nebūtina)" maxlength="24" autocomplete="nickname" title="Slapyvardis — nebūtina; jei tuščia, viešai rodysime vardą">
    <input type="email" id="contactInput" placeholder="El. paštas (mokėjimui)" maxlength="60" autocomplete="email" title="El. paštas (mokesčio instrukcijoms)">
    <input type="tel" id="phoneInput" placeholder="Telefonas (susisiekti)" maxlength="32" autocomplete="tel" inputmode="tel" title="Telefono numeris — kad galėtume susisiekti">
    <div class="pp-pay-title" style="display:none">Kaip atsiskaitysiu</div>
    <div class="pp-pay-opts" id="payMethodOpts" style="display:none">
      <label><input type="radio" name="payMethod" value="paypal" checked> PayPal</label>
      <label><input type="radio" name="payMethod" value="skrill"> Skrill</label>
      <label><input type="radio" name="payMethod" value="neteller"> Neteller</label>
      <label><input type="radio" name="payMethod" value="paysafe"> Paysafe</label>
    </div>
    <button type="button" id="joinBtn">REGISTRUOTIS</button>
    <div class="pp-reg-note" id="regNote">Slapyvardis nebūtinas. Jei vardas jau užimtas — automatiškai Jonas2, Jonas3… El. paštas ir tel. privatūs.</div>
    <div class="pp-reg-note" id="regClosedNote" style="display:none;color:#c9a227;font-weight:600;">Registracija uždaryta — Vilkas mokosi su imitaciniais pirkėjais.</div>
  </div>
  <div class="pp-done" id="ppDone" style="display:none;">
    <div class="pp-done-msg" id="ppDoneMsg"></div>
    <button type="button" class="pp-change-reg" id="ppChangeReg">Keisti / išeiti</button>
  </div>
</div>
<div class="wolf-impact" id="wolfImpact"></div>
<img class="wolf-table" id="wolfTable" src="/photos/vilkas_table.webp" alt="" aria-hidden="true">
<div class="showcase" id="showcase" aria-hidden="true"><img id="showcaseImg" alt=""><h3 id="showcaseTitle"></h3><div class="chips" id="showcaseChips"></div></div>
<div class="wolf-pop __WOLF_POP_CLASS__" id="wolfPop" aria-hidden="true">
  <div class="wolf-pop-bubble" id="wolfPopBubble"><span class="bt" id="wolfBubT"></span><span class="bs" id="wolfBubS"></span></div>
  <div class="wolf-body"><img id="wolfPopVid" class="wolf-live-anim" src="/photos/vilkas_blue_anim.webp?v=__BUILD_ID__" alt="" aria-hidden="true"><img id="wolfPopImg" src="/photos/vilkas_blue_pose.webp?v=__BUILD_ID__" alt=""><img id="wolfPopGhost" class="ghost" src="/photos/vilkas_blue_pose.webp?v=__BUILD_ID__" alt=""></div>
</div>
<div class="wolf-photo" id="wolfPhoto" aria-hidden="true"><img id="wolfPhotoImg" src="/photos/vilkas_wiki_dressed.webp?v=__BUILD_ID__" alt=""><span id="wolfPhotoCaption">Vilkas scenoje</span></div>
<button class="voice-unlock" id="voiceUnlock" type="button">🔊 Paspausk — įjungti garsą</button>
<button class="vilkas-stage-btn" id="btnVilkasStage" type="button">▶ Įjungti Vilką</button>
<audio id="vilkasRadioPlayer" src="/radio/club" preload="auto" autoplay muted playsinline style="position:absolute;width:0;height:0;opacity:0;pointer-events:none" aria-hidden="true"></audio>
<audio id="deskSongPlayer" preload="auto" playsinline style="position:absolute;width:0;height:0;opacity:0;pointer-events:none" aria-hidden="true"></audio>
<div class="celebrate-overlay" id="celebrateOverlay">
  <div class="celebrate-card">
    <button type="button" class="ui-close-x" id="celebrateCloseX" aria-label="Uždaryti">✕</button>
    <div class="celebrate-hands" id="celebrateHands">👏👏</div>
    <img class="celebrate-persona" src="/photos/vilkas_bang.webp" alt="Vilkas" width="56" height="56" style="object-fit:contain;border:none;box-shadow:none;">
    <div class="celebrate-title">PARDUOTA!</div>
    <div class="celebrate-sub">Sveikiname, <b id="celebrateName">—</b>!<br>Laimėjai už <b id="celebratePrice">—</b></div>
    <button class="celebrate-close" id="celebrateClose">Nuostabu!</button>
  </div>
</div>
<div class="stage" id="stageRoot">
  <div class="brand">
    <div class="brand-top">
      <h1 class="brand-name">Penktadienio aukcionas</h1>
      <div class="radio-badge" id="radioBadge" aria-label="Klubinė muzika">
        <button class="radio-choice active" type="button" data-radio="club"><span class="rb-top">klubo</span><span class="rb-mid">Bendruomenė</span></button>
      </div>
    </div>
    <div class="brand-evening">vakare <span class="brand-time">20:00</span></div>
  </div>
  <!-- host-bar pašalinta — tuščia juosta neberodoma -->
  <div id="hostBar" style="display:none"></div>
  <div id="hostWolf" style="display:none" aria-hidden="true"></div>
  <div id="hostBubble" style="display:none"></div>
  <img id="hostWolfImg" style="display:none" alt="">
  <button type="button" id="btnVoice" style="display:none">Balsas ON</button>
  <div class="lot-header">
    <span class="lot-tag"><span class="live-dot"></span><span id="lotTag">—</span></span>
    <span class="viewers" id="viewerCount">— dalyvių</span>
  </div>
  <div class="lock-banner" id="lockBanner"><b>Aukcionas ruošiamas</b> — žiūrėti ir registruotis galima, pirkimas ir statymai laikinai išjungti.</div>
  <div class="panel" id="mainPanel">
    <div class="countdown-overlay" id="countdownOverlay" style="display:none;">
      <div class="countdown-label">Aukcionas prasideda už</div>
      <div class="countdown-num" id="countdownNum">10</div>
      <div class="countdown-sub">Pasiruoškite — vos tik prasidės, galėsite siūlyti kainą!</div>
    </div>
    <div class="art" id="artWrap"><div class="art-empty" id="artEmpty"><div class="wait-box"><div class="wait-text">Vilkas ruošia kitą lotą — netrukus pradedame! Užsiregistruok ir būk pasiruošęs.</div><button type="button" class="bid-btn" disabled>🔴 Netrukus pradedame</button></div></div></div>
    <div class="item-body" id="itemBody" style="display:none;">
      <h1 class="item-title" id="itemTitle">—</h1>
      <p class="item-meta" id="itemMeta"></p>
      <div class="desc-box"><div class="desc-label">Apie daiktą</div><p class="desc-text" id="descText"></p></div>
      <div class="sold-banner" id="soldBanner">🔨 PARDUOTA — laimėjo <span id="soldName">—</span> už <span id="soldPrice">—</span></div>
      <div class="pay-box" id="payBox">
        <button type="button" class="ui-close-x" id="payBoxClose" aria-label="Uždaryti">✕</button>
        <div class="pay-title">Apmokėjimas laimėtojui</div>
        <div class="pay-amount">Iš viso mokėti (preke + siuntimas): <b id="payTotal">—</b></div>
        <p class="pay-wait" id="payWait">Mokėjimo el. paštai viešai nerodomi. Laimėtojas gaus instrukcijas į savo el. paštą pagal registracijoje pasirinktą sistemą (PayPal / Skrill / Neteller / Paysafe).</p>
        <div class="pay-private" id="payPrivate">
          <div><b id="payPrivLabel">—</b></div>
          <div class="ppv-mail" id="payPrivMail">—</div>
          <div class="pay-note" id="payPrivHint" style="margin:0;"></div>
        </div>
      </div>
      <div class="price-row">
        <div><div class="price-label">Dabartinė kaina</div><div class="price" id="priceNum">—<small>€</small></div></div>
        <button class="bid-btn price-bid" id="bidBtn" type="button" disabled><span id="bidLabel">KELTI KAINĄ +1 €</span></button>
        <div class="timer-ring"><svg viewBox="0 0 76 76"><circle class="timer-track" cx="38" cy="38" r="32"></circle><circle class="timer-fill" id="timerCircle" cx="38" cy="38" r="32" stroke-dasharray="201" stroke-dashoffset="0"></circle></svg><div class="timer-num" id="timerNum">1:00</div></div>
      </div>
      <div class="bidder-line" id="bidderLine"></div>
      <div class="hint">Kiekvienas pasiūlymas pratęsia laikrodį iki 1:00.</div>
      <div class="tiers"><div class="tier"><b>+1 €</b>kiekvienas statymas</div><div class="tier"><b>1:00</b>po kiekvieno statymo</div><div class="tier"><b>🏆</b>laimi paskutinis</div></div>
      <div class="rules-box">
        <div class="rules-title">Kaip veikia šis aukcionas</div>
        <ul class="rules-list">
          <li>Prieš siūlant kainą <b>būtina užsiregistruoti</b>.</li>
          <li>Vilkas pristato prekę, tada mygtukas žaliai skaičiuoja <b>9…1 — START!</b></li>
          <li>Kiekvienas pasiūlymas <b>pratęsia laikmatį iki 1:00</b>.</li>
          <li><b>Paskutinis</b> pasiūlęs, kai laikas baigiasi — <b>laimi</b>.</li>
          <li>Siuntimo kaina nurodyta prie daikto, apmokama atskirai.</li>
        </ul>
        <div class="contact-line">Kontaktai: <a href="mailto:mindaugasbusiness@gmail.com">mindaugasbusiness@gmail.com</a></div>
      </div>
      <div class="feed"><span class="feed-title">Pasiūlymų istorija</span><div class="feed-list" id="feedList"><div class="feed-empty">Kol kas tylu.</div></div></div>
    </div>
  </div>
  <div class="past-box" id="pastBox" style="display:none;"><span class="feed-title">Ankstesni lotai</span><div id="pastList"></div></div>
  <div class="foot" style="display:none" aria-hidden="true"></div>
</div>
<div class="queue-rail qr-empty" id="queueRail" aria-label="Šio vakaro prekės">
  <div class="qr-head">
    <span class="qr-title">Šio vakaro prekės</span>
    <span class="qr-sub" id="qrCount">eilės tvarka · kai baigsis viena — ateina kita</span>
  </div>
  <div class="qr-row">
    <button type="button" class="qr-arrow" id="qrPrev" aria-label="Ankstesnė">‹</button>
    <div class="qr-viewport" id="qrViewport"><div class="qr-track" id="qrTrack"></div></div>
    <button type="button" class="qr-arrow" id="qrNext" aria-label="Kita">›</button>
  </div>
</div>
<div class="qr-modal" id="qrModal" role="dialog" aria-modal="true" aria-hidden="true">
  <div class="qr-modal-card">
    <button type="button" class="qr-modal-close" id="qrModalClose" aria-label="Uždaryti">×</button>
    <img class="qr-modal-img" id="qrModalImg" alt="">
    <div class="qr-modal-ord" id="qrModalOrd"></div>
    <h3 class="qr-modal-title" id="qrModalTitle"></h3>
    <div class="qr-modal-price" id="qrModalPrice"></div>
    <p class="qr-modal-row" id="qrModalCond"></p>
    <p class="qr-modal-row" id="qrModalDef"></p>
    <p class="qr-modal-row" id="qrModalPlus"></p>
    <p class="qr-modal-row" id="qrModalInc"></p>
    <p class="qr-modal-row" id="qrModalDesc"></p>
  </div>
</div>
<script>
function reportClientError(message, source, line, column, stack){
  try{
    fetch('/api/client_error',{
      method:'POST',headers:{'Content-Type':'application/json'},keepalive:true,
      body:JSON.stringify({message:String(message||'client_error'),source:source||'',line:line||0,column:column||0,stack:stack||''})
    }).catch(function(){});
  }catch(ignore){}
}
window.onerror=function(message,source,line,column,error){
  reportClientError(message,source,line,column,error&&error.stack);
  return false;
};
window.addEventListener('unhandledrejection',function(ev){
  var r=ev&&ev.reason;
  reportClientError('Unhandled rejection: '+(r&&r.message?r.message:String(r||'')),'',0,0,r&&r.stack);
});
// ---------- garsai (Web Audio API, be joku isoriniu failu) ----------
var audioCtx = null;
function ac(){ if(!audioCtx){ audioCtx = new (window.AudioContext||window.webkitAudioContext)(); } return audioCtx; }
function beep(freq, dur, type, vol, delay){
  try{
    var ctx = ac();
    var t0 = ctx.currentTime + (delay||0);
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.type = type||'sine'; osc.frequency.setValueAtTime(freq, t0);
    gain.gain.setValueAtTime(0, t0);
    gain.gain.linearRampToValueAtTime(vol||0.2, t0+0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, t0+dur);
    osc.connect(gain); gain.connect(ctx.destination);
    osc.start(t0); osc.stop(t0+dur+0.05);
  }catch(e){}
}
function tickSound(){ beep(720, 0.09, 'square', 0.12); }
function startSound(){
  beep(440,0.14,'sawtooth',0.22,0); beep(660,0.14,'sawtooth',0.22,0.07);
  beep(880,0.4,'sawtooth',0.3,0.14);
}
function fanfareSound(){
  [523,659,784,1047].forEach(function(f,i){ beep(f,0.5,'triangle',0.22,i*0.13); });
}
function noiseBurst(t0, dur, vol){
  try{
    var ctx = ac();
    var n = Math.max(1, Math.floor(ctx.sampleRate*dur));
    var buf = ctx.createBuffer(1, n, ctx.sampleRate);
    var d = buf.getChannelData(0);
    for(var i=0;i<n;i++){ d[i] = (Math.random()*2-1) * (1 - i/n); }
    var src = ctx.createBufferSource(); src.buffer = buf;
    var filt = ctx.createBiquadFilter(); filt.type='bandpass'; filt.frequency.value=1800; filt.Q.value=0.8;
    var gain = ctx.createGain(); gain.gain.setValueAtTime(vol, t0);
    src.connect(filt); filt.connect(gain); gain.connect(ctx.destination);
    src.start(t0); src.stop(t0+dur);
  }catch(e){}
}
function applauseSound(){
  var ctx = ac(); var t0 = ctx.currentTime;
  for(var i=0;i<55;i++){
    var t = t0 + Math.pow(Math.random(),1.3)*2.2;
    noiseBurst(t, 0.035+Math.random()*0.04, 0.18+Math.random()*0.12);
  }
}
function bidApplauseSound(){
  try{
    var ctx = ac(); var t0 = ctx.currentTime;
    for(var i=0;i<42;i++){
      var t = t0 + Math.pow(Math.random(),1.15)*1.05;
      noiseBurst(t, 0.028+Math.random()*0.04, 0.2+Math.random()*0.14);
    }
    /* žaidybiniai „monetų“ dingai */
    beep(880,0.1,'square',0.11,0);
    beep(1175,0.12,'square',0.1,0.08);
    beep(1397,0.16,'triangle',0.12,0.16);
  }catch(e){}
}
function crowdOoohSound(options){
  options=options||{};
  var duration=options.duration||2.1, volume=options.volume||0.075;
  var ctx = ac(); var t0 = ctx.currentTime;
  [220,277,330,415].forEach(function(f){
    var osc = ctx.createOscillator(); var gain = ctx.createGain();
    osc.type='sawtooth'; osc.frequency.setValueAtTime(f*0.82, t0);
    osc.frequency.linearRampToValueAtTime(f, t0+0.45);
    var filt = ctx.createBiquadFilter(); filt.type='lowpass'; filt.frequency.value=1000;
    gain.gain.setValueAtTime(0,t0);
    gain.gain.linearRampToValueAtTime(volume, t0+0.35);
    gain.gain.linearRampToValueAtTime(volume, t0+duration*0.65);
    gain.gain.exponentialRampToValueAtTime(0.001, t0+duration);
    osc.connect(filt); filt.connect(gain); gain.connect(ctx.destination);
    osc.start(t0); osc.stop(t0+duration+0.1);
  });
}
function celebrationSound(){ crowdOoohSound(); applauseSound(); setTimeout(fanfareSound, 250); }

// ---------- kūjis + žaidimo muzika + LT vedėjas ----------
var voiceOn = localStorage.getItem('host_voice') !== '0';
var musicOn = true; // bliuzas fone visada – mygtuko UI nėra
var deskSongOn = false; /* paspausta daina — radijas tyliai, daina groja */
var deskSongN = 0;
var vilkasStageOn = false; /* įžangos viršelis kol Mindaugas neįjungia Vilko */
function getDeskSongEl(){ return document.getElementById('deskSongPlayer'); }
var deskSongNextBusy=false;
function bindDeskSongEnded(){
  var s=getDeskSongEl();
  if(!s || s._deskNextBound) return;
  s._deskNextBound=true;
  s.addEventListener('ended', function(){
    /* Pasibaigus — KITA daina, ne ta pati. Tik audio master keičia serverį. */
    if(!deskSongOn || !deskSongN) return;
    if(typeof isAudioMaster==='function' && !isAudioMaster()) return;
    if(deskSongNextBusy) return;
    deskSongNextBusy=true;
    fetch('/api/desk_song/next', {method:'POST', cache:'no-store'}).then(function(r){ return r.json(); }).then(function(d){
      deskSongNextBusy=false;
      if(d && d.ok){
        try{ applyDeskSong({desk_song: d.song || null}); }catch(e){}
      }
    }).catch(function(){ deskSongNextBusy=false; });
  });
}
function applyDeskSong(st){
  bindDeskSongEnded();
  var song = st && st.desk_song ? st.desk_song : null;
  var n = song ? (Number(song.n)||0) : 0;
  var url = song && song.url ? String(song.url) : (n ? ('/desk-songs/'+n) : '');
  if(n===deskSongN && !!n===deskSongOn){
    if(deskSongOn){
      var sKeep=getDeskSongEl();
      /* Pasibaigus NEKARTOTI tos pačios — paleisti next */
      if(sKeep && sKeep.ended){
        if(typeof isAudioMaster==='function' && isAudioMaster() && !deskSongNextBusy){
          deskSongNextBusy=true;
          fetch('/api/desk_song/next', {method:'POST', cache:'no-store'}).then(function(r){ return r.json(); }).then(function(d){
            deskSongNextBusy=false;
            if(d && d.ok) applyDeskSong({desk_song: d.song || null});
          }).catch(function(){ deskSongNextBusy=false; });
        }
        return;
      }
      if(sKeep && sKeep.paused && !(typeof stageMusicMuted==='function' && stageMusicMuted())){
        try{ var pk=sKeep.play(); if(pk&&pk.catch) pk.catch(function(){}); }catch(e){}
      }
    }
    return;
  }
  deskSongN=n;
  deskSongOn=n>0;
  var s=getDeskSongEl();
  if(!s) return;
  if(!deskSongOn){
    try{ s.pause(); s.removeAttribute('src'); s.load(); }catch(e){}
    var r=getRadioEl && getRadioEl();
    if(r){ try{ r.muted=false; r.volume=radioVolumeForCurrentState(); }catch(e){} }
    try{ if(typeof keepRadioAlive==='function') keepRadioAlive(); }catch(e){}
    return;
  }
  try{ if(typeof softPauseRadioKeepSrc==='function') softPauseRadioKeepSrc(); }catch(e){}
  var rad=getRadioEl && getRadioEl();
  if(rad){ try{ rad.muted=true; rad.volume=0; }catch(e){} }
  if(typeof stageMusicMuted==='function' && stageMusicMuted()){ try{ s.pause(); }catch(e){} return; }
  try{
    if((s.currentSrc||s.src||'').indexOf(url)<0){ s.src=url; }
    s.loop=false; /* baigėsi → kita daina (ended handler) */
    s.muted=false; s.volume=vilkasStageOn ? DESK_SONG_VOL*0.10 : (announceBusy ? DESK_SONG_VOL*MUSIC_DUCK_RATIO : DESK_SONG_VOL);
    var p=s.play(); if(p&&p.catch) p.catch(function(){});
  }catch(e){}
}
function isVilkasStageOn(){ return !!vilkasStageOn; }
function syncCoverMode(){
  try{ document.body.classList.toggle('cover-mode', !vilkasStageOn); }catch(e){}
  var btn=document.getElementById('btnVilkasStage');
  if(btn){
    btn.classList.toggle('on', !!vilkasStageOn);
    btn.textContent = vilkasStageOn ? '■ Vilkas ON — išjungti' : '▶ Įjungti Vilką';
  }
  var vu=document.getElementById('voiceUnlock');
  if(vu && vilkasStageOn) vu.textContent='🔊 Paspausk — įjungti Vilko 8 balsą';
  else if(vu) vu.textContent='🔊 Paspausk — įjungti garsą';
  try{
    if(!vilkasStageOn){
      if(typeof ensureIntroMedia==='function') ensureIntroMedia();
      else if(typeof startDiscoBeat==='function') startDiscoBeat();
    } else {
      /* F9 Vilkas ON: disco vizualas OFF, radijas tik AUDIO MASTER (1 tabas) */
      try{ if(typeof stopDiscoBeat==='function') stopDiscoBeat(); }catch(e2){}
      try{
        musicOn=true; radioArmed=true; pageAudioOk=true;
        if(isAudioMaster()){
          if(typeof keepRadioAlive==='function') keepRadioAlive();
          else if(typeof startMusic==='function') startMusic(false);
        } else {
          softPauseRadioKeepSrc();
        }
      }catch(e2){}
    }
  }catch(e){}
  try{
    if(!vilkasStageOn && typeof closeQrModal==='function') closeQrModal();
  }catch(e){}
  var vuHide=document.getElementById('voiceUnlock');
  if(vuHide && !vilkasStageOn) vuHide.classList.remove('show');
}
function setVilkasStageFromState(st){
  var next=!!(st && st.vilkas_stage_on);
  if(next===vilkasStageOn){ syncCoverMode(); return; }
  vilkasStageOn=next;
  syncCoverMode();
  setMusicDuck(vilkasStageOn);
  if(vilkasStageOn){
    try{ interruptAllSpeech(); }catch(e){}
    try{ heardWelcome=false; }catch(e){}
    try{ heardLotIntro={}; }catch(e){}
    stopIntroMediaRetry();
    try{ keepVilkasOnStage(); }catch(e){}
    try{
      musicOn=true; radioArmed=true; pageAudioOk=true;
      if(isAudioMaster() && typeof keepRadioAlive==='function') keepRadioAlive();
    }catch(e){}
    try{
      (pendingStageEvents||[]).splice(0).forEach(function(ev){ try{ handleServerEvent(ev); }catch(e2){} });
    }catch(e){}
  }
  if(!vilkasStageOn){
    try{interruptAllSpeech();}catch(e){}
    try{wolfIdle();}catch(e){}
    try{ keepVilkasOnStage(); }catch(e){}
    /* F10 → įžanga: priverstinai muzika + šokėjos (ne tik CSS cover-mode) */
    try{ if(typeof releaseRadioAnalyser==='function') releaseRadioAnalyser(); }catch(eR){}
    try{ if(typeof ensureIntroMedia==='function') ensureIntroMedia(true); }catch(eI){}
    try{ if(typeof keepDancerVideoAlive==='function') keepDancerVideoAlive(); }catch(eD){}
  }
  try{ if(typeof render==='function' && state) render(); }catch(e){}
}
(function(){
  /* Vilkas ON/OFF — TIK klaviatūra PC (F9/F10 globalus daemon). Ne Chrome. */
  var b=document.getElementById('btnVilkasStage');
  if(!b) return;
  b.onclick=function(){
    var want=!vilkasStageOn;
    var pass=prompt(want?'Įvesk admin slaptažodį — įjungti Vilką:':'Įvesk admin slaptažodį — grįžti į viršelį:');
    if(pass==null) return;
    b.disabled=true;
    fetch('/api/admin/vilkas_stage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass,on:want})})
      .then(function(r){ if(!r.ok) return r.json().then(function(d){ throw new Error(d.detail||'Nepavyko'); }); return r.json(); })
      .then(function(d){
        vilkasStageOn=!!d.vilkas_stage_on;
        syncCoverMode();
        if(typeof poll==='function') poll();
      })
      .catch(function(e){ alert(e.message||'Nepavyko'); })
      .finally(function(){ b.disabled=false; });
  };
})();
syncCoverMode();
var musicNodes = null;
var lastBidKey = null;
var announceBusy = false;
var announceCurrentJob = null;
var announceQueue = [];
var announceEpoch = 0;
var ltVoice = null;
var AUDIO_MASTER_KEY='vilkas_audio_master_v3';
var AUDIO_KILL_KEY='vilkas_audio_kill_v3';
var audioTabId='tab_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2);
var radioArmed=false;
var pageAudioOk=true;
var radioBus=null;
try{ radioBus=new BroadcastChannel('vilkas_audio_v3'); }catch(e){}
function isCoverMode(){
  try{ return document.body.classList.contains('cover-mode'); }catch(e){ return false; }
}
function readAudioMaster(){
  try{return JSON.parse(localStorage.getItem(AUDIO_MASTER_KEY)||'null');}catch(e){return null;}
}
function isAudioMaster(){
  /* Įžanga — VISADA master. Jokio blokavimo iš kito tabo. */
  if(isCoverMode()) return true;
  var m=readAudioMaster();
  return !!(m && m.id===audioTabId && Date.now()-Number(m.at||0)<7000);
}
function shoutKillOthers(){
  /* Įžangoje NEŽUDYTI kitų — jokių blokavimų */
  if(isCoverMode()) return;
  try{ localStorage.setItem(AUDIO_KILL_KEY, JSON.stringify({id:audioTabId,at:Date.now()})); }catch(e){}
  try{ if(radioBus) radioBus.postMessage({type:'kill',id:audioTabId}); }catch(e){}
}
function otherHoldsMaster(){
  if(isCoverMode()) return false;
  try{
    var m=readAudioMaster();
    return !!(m && m.id && m.id!==audioTabId && (Date.now()-Number(m.at||0))<7000);
  }catch(e){ return false; }
}
function claimAudioMaster(force){
  if(isCoverMode()){
    try{localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()}));}catch(e){}
    return true;
  }
  if(!force && otherHoldsMaster()) return false;
  shoutKillOthers();
  try{localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()}));}catch(e){}
  return isAudioMaster();
}
function releaseAudioMaster(){
  if(isCoverMode()) return;
  try{
    var m=readAudioMaster();
    if(m && m.id===audioTabId) localStorage.removeItem(AUDIO_MASTER_KEY);
  }catch(e){}
}
function pageAllowsAudio(){
  try{
    if(document.visibilityState==='hidden') return false;
    return !!pageAudioOk;
  }catch(e){ return true; }
}
function softPauseRadioKeepSrc(){
  /* Pauzė BE src wipe — grįžus garsas iškart */
  try{
    var el=document.getElementById('vilkasRadioPlayer');
    if(el && !el.paused) el.pause();
  }catch(e){}
}
/* Mindaugas 2026-10-08: Vilko scenoje (F9) muzika OFF — nemaišo balsui/bajeriams/telefonui/gitarai.
   Tik soft pause + mute, src NEliečiamas; F10 įžangoje radijas grįžta. */
var STAGE_MUSIC_OFF = true;
/* Įžangoje radijas ON; F9 scenoje tyli (STAGE_MUSIC_OFF). MUSIC_OFF_ALL=true = tyli ir įžanga. */
/* Praktika (practice_bots): muzika ON scenoje — Vilkas girdi ir mokosi padainuoti. */
var MUSIC_OFF_ALL = false;
var practiceModeOn = false;
function stageMusicMuted(){
  return !!MUSIC_OFF_ALL;
}
function radioVolumeForCurrentState(){
  if(stageMusicMuted()) return 0;
  if(vilkasStageOn) return radioTargetVol*0.10;
  return announceBusy ? radioDuckVol : radioTargetVol;
}
function muteMusicForStage(){
  softPauseRadioKeepSrc();
  try{
    var el=document.getElementById('vilkasRadioPlayer');
    if(el){ el.muted=true; el.volume=0; }
  }catch(e){}
  try{
    var ds=document.getElementById('deskSongPlayer');
    if(ds && !ds.paused) ds.pause();
  }catch(e){}
}
function hardKillRadio(){
  /* Įžangoje IR Vilko scenoje (F9) DRAUDŽIAMA naikinti srautą — tik soft pause */
  if(isCoverMode() || vilkasStageOn){ softPauseRadioKeepSrc(); radioStarting=false; return; }
  radioStarting=false;
  try{ if(typeof stopEnergyWatch==='function') stopEnergyWatch(); }catch(e){}
  try{ if(typeof stopDiscoBeat==='function') stopDiscoBeat(); }catch(e){}
  releaseRadioAnalyser();
  var el=document.getElementById('vilkasRadioPlayer');
  if(!el) return;
  try{
    el.pause();
    el.onplaying=null;
    el.onerror=null;
    el.removeAttribute('src');
    el.load();
  }catch(e){}
}
function silenceThisTab(){
  /* Įžanga: JOKIO blokavimo / kill iš kitų tabų */
  if(isCoverMode()) return;
  try{interruptAllSpeech();}catch(e){
    try{if(hostAudio){hostAudio.pause();hostAudio=null;}}catch(e2){}
    try{if(phoneRingAudio){phoneRingAudio.pause();phoneRingAudio=null;}}catch(e2){}
    try{if(window.speechSynthesis)speechSynthesis.cancel();}catch(e2){}
  }
  try{hardKillRadio();}catch(e){}
}
function onPageAudioSuspend(){
  pageAudioOk=false;
  if(isCoverMode()){
    softPauseRadioKeepSrc();
    return;
  }
  silenceThisTab();
  releaseAudioMaster();
}
function onPageAudioResume(){
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  try{ if(isCoverMode() && typeof ensureIntroMedia==='function') ensureIntroMedia(); }catch(e){}
  try{
    if(vilkasStageOn && musicOn && isAudioMaster()){
      if(typeof keepRadioAlive==='function') keepRadioAlive();
    }
  }catch(e){}
}
setInterval(function(){
  if(document.visibilityState==='hidden'){
    if(isCoverMode()){ softPauseRadioKeepSrc(); return; }
    if(pageAudioOk) onPageAudioSuspend();
    else { try{hardKillRadio();}catch(e){} }
    return;
  }
  pageAudioOk=true;
  /* Įžanga: visada muzika. Vilkas scenoje: muzika TIK audio-master tab'e (kad balsas nesidubliuotų). */
  if(deskSongOn){
    try{ keepRadioAlive(); }catch(e){}
    return;
  }
  if(musicOn && isCoverMode()){
    claimAudioMaster(true);
    try{ keepRadioAlive(); }catch(e){}
  } else if(musicOn && vilkasStageOn){
    if(isAudioMaster()){
      try{ localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()})); }catch(e){}
      try{ keepRadioAlive(); }catch(e){}
    } else {
      try{ softPauseRadioKeepSrc(); }catch(e){}
      announceQueue=[]; announceBusy=false; announceCurrentJob=null;
    }
  } else if(isAudioMaster()){
    try{localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()}));}catch(e){}
  } else if(otherHoldsMaster()){
    try{hardKillRadio();}catch(e){}
  }
},700);
window.addEventListener('storage',function(e){
  if(isCoverMode()) return; /* jokių kill/master blokų įžangoje */
  if(e.key===AUDIO_MASTER_KEY && !isAudioMaster()) silenceThisTab();
  if(e.key===AUDIO_KILL_KEY){
    try{
      var k=JSON.parse(e.newValue||'null');
      if(k && k.id && k.id!==audioTabId) silenceThisTab();
    }catch(err){}
  }
});
try{
  if(radioBus) radioBus.onmessage=function(ev){
    if(isCoverMode()) return;
    var d=ev && ev.data;
    if(d && d.type==='kill' && d.id!==audioTabId) silenceThisTab();
  };
}catch(e){}
document.addEventListener('visibilitychange',function(){
  if(document.visibilityState==='hidden') onPageAudioSuspend();
  else onPageAudioResume();
});
window.addEventListener('pagehide',function(){ onPageAudioSuspend(); });
window.addEventListener('freeze',function(){ onPageAudioSuspend(); });

function unlockAudio(ev){
  if(document.visibilityState==='hidden') return;
  try{
    if(ev && ev.target && ev.target.closest && ev.target.closest('[data-radio]')) return;
  }catch(e){}
  pageAudioOk=true;
  radioArmed=true;
  musicOn=true;
  claimAudioMaster(true);
  try{
    var c=ac();
    if(c.state==='suspended') c.resume();
  }catch(e){}
  if(window.speechSynthesis) speechSynthesis.getVoices();
  try{ makeRadioAudibleNow(); }catch(e){}
  var vb=document.getElementById('voiceUnlock');
  if(vb && isCoverMode()) vb.classList.remove('show');
}
document.addEventListener('pointerdown', unlockAudio, {once:false, capture:true});
document.addEventListener('click', unlockAudio, {once:false, capture:true});
document.addEventListener('touchstart', unlockAudio, {once:false, capture:true});
document.addEventListener('keydown', unlockAudio, {once:false, capture:true});
/* scroll / wheel — Chrome neleidžia autoplay, bet kartais padeda AudioContext */
document.addEventListener('wheel', function(){ try{ var c=ac(); if(c.state==='suspended') c.resume(); }catch(e){} }, {passive:true, capture:true});

/* Paštas / tel — be Windows „How do you want to open this?“ (mailto be pašto programos) */
(function(){
  var GMAIL='https://mail.google.com/mail/?view=cm&fs=1&to=mindaugasbusiness@gmail.com&su=Penktadienio%20aukcionas';
  var TEL='tel:+37066331913';
  var PHONE='+37066331913';
  var lastAt=0, lastKey='';
  function isPhoneLike(){
    try{
      if(navigator.userAgentData && navigator.userAgentData.mobile) return true;
    }catch(e){}
    var touch=(navigator.maxTouchPoints||0)>0;
    var narrow=Math.min(screen.width||0,screen.height||0)<=920;
    return touch && narrow;
  }
  function toast(msg){
    var el=document.getElementById('contactToast');
    if(!el){
      el=document.createElement('div');
      el.id='contactToast';
      document.body.appendChild(el);
    }
    el.textContent=msg;
    el.classList.add('show');
    clearTimeout(toast._t);
    toast._t=setTimeout(function(){ el.classList.remove('show'); }, 2800);
  }
  function openContactLink(e){
    try{
      var t=e.target;
      if(!t || !t.closest) return;
      var a=t.closest('#discoMailLink, #discoTelLink, #discoContacts a.disco-contact-a, .aqr-contact a, .contact-line a');
      if(!a) return;
      var href=(a.getAttribute('href')||'').trim();
      var isMail=a.id==='discoMailLink' || /mailto:|mail\.google\.com/i.test(href) || /@/.test(a.textContent||'');
      var isTel=a.id==='discoTelLink' || /^tel:/i.test(href) || a.hasAttribute('data-phone');
      if(!isMail && !isTel) return;
      var key=isTel?'tel':'mail';
      var now=Date.now();
      if(key===lastKey && (now-lastAt)<900){ e.preventDefault(); e.stopPropagation(); return; }
      lastAt=now; lastKey=key;
      e.preventDefault();
      e.stopPropagation();
      if(isMail){
        /* HTTPS Gmail rašymas — veikia Chrome/Edge be pašto programos */
        window.open(GMAIL, '_blank', 'noopener');
        return;
      }
      if(isPhoneLike()){
        window.location.href=TEL;
        return;
      }
      /* PC: tel: kelia Windows dialogo — kopijuojam numerį */
      var num=a.getAttribute('data-phone')||PHONE;
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(num).then(function(){
          toast('Numeris nukopijuotas: '+num+' — skambinkite arba įklijuokite į Phone Link');
        }).catch(function(){ toast('Tel.: '+num); });
      }else{
        toast('Tel.: '+num);
      }
    }catch(err){}
  }
  document.addEventListener('click', openContactLink, true);
})();

function pickLtVoice(){
  if(!window.speechSynthesis) return null;
  var voices = speechSynthesis.getVoices()||[];
  return voices.find(function(v){return /^lt/i.test(v.lang);})
    || voices.find(function(v){return /lithuan|lietuvi/i.test(v.name);})
    || voices.find(function(v){return /Google.*(lt|Lith)/i.test(v.name);})
    || null;
}
if(window.speechSynthesis){
  speechSynthesis.onvoiceschanged = function(){ ltVoice = pickLtVoice(); };
  ltVoice = pickLtVoice();
}

function hammerSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var osc=ctx.createOscillator(), g=ctx.createGain();
    osc.type='sine';
    osc.frequency.setValueAtTime(140,t0);
    osc.frequency.exponentialRampToValueAtTime(45,t0+0.22);
    g.gain.setValueAtTime(0.001,t0);
    g.gain.linearRampToValueAtTime(0.55,t0+0.015);
    g.gain.exponentialRampToValueAtTime(0.001,t0+0.35);
    osc.connect(g); g.connect(ctx.destination);
    osc.start(t0); osc.stop(t0+0.4);
    noiseBurst(t0, 0.08, 0.35);
    noiseBurst(t0+0.02, 0.05, 0.2);
  }catch(e){}
}
var gongAudio = null;
var gongTimer = null;
function gongSoundSynth(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var out=ctx.createGain(); out.gain.value=0.62; out.connect(ctx.destination);
    [[78,1.15,6.2],[98,1,5.5],[146,.75,4.8],[196,.55,4.2],[247,.42,3.5],[311,.32,2.8],[392,.22,2.1],[523,.16,1.5]].forEach(function(p){
      var o=ctx.createOscillator(), g=ctx.createGain();
      o.type='sine';
      o.frequency.setValueAtTime(p[0]*1.04, t0);
      o.frequency.exponentialRampToValueAtTime(p[0], t0+0.35);
      var lfo=ctx.createOscillator(), lg=ctx.createGain(); lfo.frequency.value=2.6+Math.random()*1.8; lg.gain.value=p[0]*0.005;
      lfo.connect(lg); lg.connect(o.frequency); lfo.start(t0); lfo.stop(t0+p[2]);
      g.gain.setValueAtTime(0.0001,t0);
      g.gain.exponentialRampToValueAtTime(p[1],t0+0.018);
      g.gain.exponentialRampToValueAtTime(0.0001,t0+p[2]);
      o.connect(g); g.connect(out); o.start(t0); o.stop(t0+p[2]+0.1);
    });
    noiseBurst(t0, 0.14, 0.55);
    noiseBurst(t0+0.03, 0.08, 0.28);
  }catch(e){}
}
function gongSound(){
  /* ElevenLabs brass/auction gong — pirkimas / vilko gongo smūgis */
  try{
    if(gongAudio){ try{ gongAudio.pause(); }catch(e0){} gongAudio=null; }
    var a=new Audio('/photos/vilkas_gong.mp3?v=1');
    a.volume=0.92;
    gongAudio=a;
    var p=a.play();
    if(p&&p.catch){ p.catch(function(){ gongSoundSynth(); }); }
    return;
  }catch(e){ gongSoundSynth(); }
}
function hitGong(){
  try{ hammerStrike(); }catch(e){}
  clearTimeout(gongTimer);
  gongTimer=setTimeout(function(){ gongTimer=null; try{ gongSound(); }catch(e2){} }, 55);
}
/* Tikroviškas telefonas: MP3 skambutis + vibracija */
var phoneRingAudio = null;
function phoneRingSynth(rings){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    rings = rings || 2;
    for(var r=0;r<rings;r++){
      var start=t0 + r*1.15;
      [440,480].forEach(function(freq){
        var o=ctx.createOscillator(), g=ctx.createGain();
        o.type='sine'; o.frequency.value=freq;
        g.gain.setValueAtTime(0.0001, start);
        g.gain.linearRampToValueAtTime(0.28, start+0.03);
        g.gain.setValueAtTime(0.28, start+0.55);
        g.gain.exponentialRampToValueAtTime(0.0001, start+0.72);
        o.connect(g); g.connect(ctx.destination);
        o.start(start); o.stop(start+0.8);
      });
      /* vibracijos „buzz“ */
      var n=ctx.createBufferSource(), nb=ctx.createBuffer(1, Math.floor(ctx.sampleRate*0.7), ctx.sampleRate);
      var ch=nb.getChannelData(0);
      for(var i=0;i<ch.length;i++) ch[i]=(Math.random()*2-1)*0.4;
      n.buffer=nb;
      var ng=ctx.createGain(), filt=ctx.createBiquadFilter();
      filt.type='bandpass'; filt.frequency.value=180; filt.Q.value=4;
      ng.gain.setValueAtTime(0.0001, start);
      ng.gain.linearRampToValueAtTime(0.35, start+0.05);
      ng.gain.exponentialRampToValueAtTime(0.0001, start+0.7);
      n.connect(filt); filt.connect(ng); ng.connect(ctx.destination);
      n.start(start); n.stop(start+0.75);
    }
  }catch(e){}
}
function phoneVibratePulse(){
  try{
    if(navigator.vibrate){
      /* skambutis: vibr-vibr — pauzė — vibr-vibr */
      navigator.vibrate([220,80,220,400,220,80,220]);
    }
  }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){
      pop.classList.add('phone-ring');
      setTimeout(function(){ pop.classList.remove('phone-ring'); }, 2600);
    }
  }catch(e2){}
}
function phoneRingSound(){
  if(!pageAllowsAudio() || !isAudioMaster()) return;
  phoneVibratePulse();
  try{
    if(phoneRingAudio){ try{ phoneRingAudio.pause(); }catch(e0){} phoneRingAudio=null; }
    var a=new Audio('/photos/vilkas_phone_ring.mp3?v=1');
    a.volume=0.95;
    phoneRingAudio=a;
    var p=a.play();
    if(p&&p.catch){ p.catch(function(){ if(pageAllowsAudio()) phoneRingSynth(2); }); }
    return;
  }catch(e){ phoneRingSynth(2); }
}
var phoneTradeTimer = null;
var phoneSpeechTimer = null;
var phoneCallActive = false, phoneCallSince = 0;
var phoneSessionActive = false;
var phoneBidHold = []; /* [{name,amount,at}] — kas kėlė kol Vilkas telefone */
function setPhoneCallActive(v){ phoneCallActive=!!v; phoneCallSince=v?Date.now():0; }
function isPhoneBusy(){
  if(phoneSessionActive || phoneCallActive || phoneAway) return true;
  if(phoneSpeechTimer || phoneAwayTimer) return true;
  if(announceBusy && announceCurrentJob && (announceCurrentJob.tag==='phone'||announceCurrentJob.tag==='phone_catchup')) return true;
  try{ if(announceQueueHasTag('phone')||announceQueueHasTag('phone_catchup')) return true; }catch(e){}
  return false;
}
var phoneAway=false, phoneAwayTimer=null;
function beginPhoneSession(){
  phoneSessionActive=true;
  phoneBidHold=[];
  setPhoneCallActive(true);
}
function phoneExcuseLine(){
  return pickNR('phoneExcuse',[
    'Atsiprašau, žmonės — aš trumpai einu pakalbėti.',
    'Atsiprašau, žmonės! Telefonas — trumpam nuklysiu pakalbėti.',
    'Žmonės, atsiprašau — skambutis, einu trumpai pakalbėti.'
  ]);
}
function phoneBossReturnLine(){
  return pickNR('phoneBossReturn',[
    'Viršininkas skambino, sako… O o — kas yra, ko neperka žmonės?',
    'Viršininkas skambino! Sako — o o, kas yra, ko neperka žmonės?',
    'Buvo viršininkas. Sako: o o, kas čia — ko žmonės neperka?',
    'Viršininkas skambino, klausia… O o kas yra, ko neperka žmonės?'
  ]);
}
function hideVilkasPhoneAway(){
  /* F11: Vilkas dingsta į dūmus net scenoje (phoneAway) — keepVilkasOnStage neliečia. */
  phoneAway=true;
  try{ clearTimeout(wolfHideTimer); }catch(e){}
  try{ setBubble('', ''); }catch(e){}
  try{ stopGestures(); }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){
      pop.classList.remove('talking','lean','coffee','side','idle','alive','show','has-video');
      pop.classList.add('hide');
    }
  }catch(e){}
  /* Priverstiniai dūmai — enterSmokeBreak kitaip gali return dėl announceBusy. */
  try{
    wolfInSmoke=true;
    var field=document.getElementById('smokeField');
    if(field) field.classList.add('on');
    puffSmoke(5);
  }catch(e){}
}
function showVilkasAfterPhone(){
  phoneAway=false;
  try{ clearSmoke(); }catch(e){}
  try{ wolfPopShow('glasses'); }catch(e){}
}
function phoneCatchupLine(names){
  var list='';
  try{
    var uniq=[];
    for(var i=0;i<(names||[]).length;i++){
      var n=String(names[i]||'').trim().split(/\s+/)[0];
      if(!n) continue;
      var low=n.toLowerCase();
      var seen=false;
      for(var j=0;j<uniq.length;j++){ if(uniq[j].toLowerCase()===low){ seen=true; break; } }
      if(!seen) uniq.push(n);
    }
    if(!uniq.length) return '';
    if(uniq.length===1) list=uniq[0];
    else if(uniq.length===2) list=uniq[0]+' ir '+uniq[1];
    else list=uniq.slice(0,-1).join(', ')+' ir '+uniq[uniq.length-1];
  }catch(e){ return ''; }
  return pickNR('phoneCatchup',[
    'O kol kalbėjau telefonu, pakėlė '+list+'. Šaunuoliai!',
    'Kol buvau telefone — '+list+' pakėlė. Kas dar?',
    'Atsiprašau, telefonas… O tuo metu pakėlė '+list+'! Šaunuoliai, šaunuoliai!',
    'Alio baigta. Kol aš telefone, pakėlė '+list+'. Nestabdom!',
    'Oho — kol telefonavau, '+list+' jau spaudė! Brawo!'
  ]);
}
function endPhoneSessionAndCatchup(){
  setPhoneCallActive(false);
  phoneAway=false;
  try{ clearTimeout(phoneAwayTimer); phoneAwayTimer=null; }catch(e){}
  var held=phoneBidHold.slice();
  phoneBidHold=[];
  var names=[];
  for(var i=0;i<held.length;i++) names.push(held[i].name);
  var catchup=phoneCatchupLine(names);
  function finishPhoneSession(){
    phoneSessionActive=false;
  }
  function afterBoss(){
    if(!catchup){ finishPhoneSession(); return; }
    queueAnnounce(catchup,{
      tag:'phone_catchup', priority:true, pose:'raise', bangs:0, fast:true, fx:'cheer',
      gestures:['raise','thumb','clap'], gestureMs:340,
      bubble:'📞→🔔 Kol telefone…',
      onDone:function(){ try{ finishPhoneSession(); }catch(e){} }
    });
  }
  /* Sesija lieka ON kol baigsis viršininkas (+ catchup) — kitaip bid'ai perkerta balsą. */
  try{ if(typeof claimAudioMaster==='function') claimAudioMaster(true); }catch(eM){}
  queueAnnounce(phoneBossReturnLine(),{
    tag:'phone', priority:true, pose:'glasses', bangs:0, fast:true,
    gestures:['glasses','raise','thumb'], bubble:'📞 Viršininkas…',
    onDone:function(){ try{ afterBoss(); }catch(e){ finishPhoneSession(); } }
  });
}
function holdBidDuringPhone(name, amount){
  /* Gongas+burbulas OK; balsas — NE (tik catchup po skambučio). */
  var nm=String(name||'Dalyvis').trim()||'Dalyvis';
  var am=Number(amount)||0;
  try{ hitGong(); }catch(e){}
  try{ cheerBurst(); }catch(e){}
  try{ setBubble('🔔 '+nm+' → '+Math.round(am)+' €', ''); }catch(e){}
  /* Naujesnis to paties vardo — pakeičia seną */
  var low=nm.toLowerCase();
  for(var i=phoneBidHold.length-1;i>=0;i--){
    if(String(phoneBidHold[i].name||'').toLowerCase()===low) phoneBidHold.splice(i,1);
  }
  phoneBidHold.push({name:nm, amount:am, at:Date.now()});
}
/* Savigyda: skambučio vėliava negali kabėti — kitaip F11 / eilė miršta.
   Sesijos metu (F11) — ilgesnis limitas; catchup po onDone. */
setInterval(function(){
  if(!phoneCallActive || !phoneCallSince) return;
  var age=Date.now()-phoneCallSince;
  var softLimit=phoneSessionActive?90000:8000;
  var hardLimit=phoneSessionActive?120000:20000;
  if(age>hardLimit){
    setPhoneCallActive(false);
    if(phoneSessionActive){ try{ endPhoneSessionAndCatchup(); }catch(e){ phoneSessionActive=false; phoneBidHold=[]; } }
    return;
  }
  if(age>softLimit && !announceBusy && !hostAudio && !phoneSpeechTimer){
    setPhoneCallActive(false);
    if(phoneSessionActive){ try{ endPhoneSessionAndCatchup(); }catch(e){ phoneSessionActive=false; phoneBidHold=[]; } }
  }
}, 1000);
/* Gitaros riffas (WebAudio) turi savo master gain — kad interrupt jį nutildytų, o ne grotų po balsu. */
var riffMaster=null;
function stopGuitarRiff(){
  try{
    if(!riffMaster) return;
    var m=riffMaster; riffMaster=null; var t=m.context.currentTime;
    m.gain.cancelScheduledValues(t); m.gain.setValueAtTime(m.gain.value,t); m.gain.linearRampToValueAtTime(0.0001,t+0.15);
    setTimeout(function(){ try{ m.disconnect(); }catch(e){} },260);
  }catch(e){}
}
function playPhoneCallGag(kind){
  /* Skambutis: tyla komentarams; po Alio — catchup kas pakėlė. */
  if(phoneCallActive || phoneSessionActive || hostAudio || announceBusy || announceQueue.length) return;
  beginPhoneSession();
  try{ phoneRingSound(); }catch(e){}
  clearTimeout(phoneSpeechTimer);
  phoneSpeechTimer=setTimeout(function(){
    phoneSpeechTimer=null;
    try{
      if(phoneRingAudio){ phoneRingAudio.pause(); phoneRingAudio.currentTime=0; phoneRingAudio=null; }
      if(navigator.vibrate) navigator.vibrate(0);
    }catch(e1){}
    try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e1){}
    setPhoneCallActive(false);
    try{ if(typeof claimAudioMaster==='function') claimAudioMaster(true); }catch(eM){}
    var line;
    if(kind==='trade'){
      line=pick([
        'Alio, alio! Aš blogai tave girdžiu — aš judesyje, perk telefonus!',
        'Alio, alio! Blogai girdžiu! Aš judesyje — telefonų prekyba, netrukdyk!',
        'Alio, alio! Aš judesyje, perk telefonus — blogai tave girdžiu, paskui!'
      ]);
    } else {
      line=pick([
        'Alio, alio! Aš darbe — kaip kokiam darbe? Penktadienio aukcione! Prekyba, prekyba užsiėmu — gerai, netrukdyk!',
        'Alio, alio! Gerai, aš perskambinsiu. Netrukdyk!',
        'Alio, alio! Aš darbe, Penktadienio aukcione — prekyba užsiėmu. Gerai, netrukdyk!'
      ]);
    }
    queueAnnounce(line, {
      tag:'phone', pose:'glasses', bangs:0,
      gestures:['glasses','wink','raise'],
      bubble: kind==='trade' ? '📞 Alio! Judesyje…' : '📞 Alio, alio!',
      onDone:function(){ try{ endPhoneSessionAndCatchup(); }catch(e){} }
    });
  }, 2700);
}
function scheduleTradePhoneCall(){
  clearTimeout(phoneTradeTimer);
  /* Retas trečias pokalbis: tik po tikro pakėlimo ir tik pasibaigus balsui. */
  if(Math.random() > 0.28) return;
  phoneTradeTimer=setTimeout(function waitForQuiet(){
    if(hostAudio || phoneCallActive || announceBusy || announceQueue.length){
      phoneTradeTimer=setTimeout(waitForQuiet, 1200);
      return;
    }
    playPhoneCallGag('trade');
  }, 6500);
}
function isFemaleName(name){
  var w=String(name||'').trim().split(/\s+/)[0].toLowerCase();
  if(!w) return false;
  if(/(as|is|ys|us|ius|jus)$/.test(w)) return false;
  return /(a|ė|e|ia|ija)$/.test(w);
}
function vocative(name){
  var w=String(name||'').trim().split(/\s+/)[0];
  if(/ius$/i.test(w)) return w.replace(/ius$/i,'iau');
  if(/as$/i.test(w)) return w.replace(/as$/i,'ai');
  if(/is$/i.test(w)) return w.replace(/is$/i,'i');
  if(/ys$/i.test(w)) return w.replace(/ys$/i,'y');
  if(/us$/i.test(w)) return w.replace(/us$/i,'au');
  if(/ė$/i.test(w)) return w.replace(/ė$/i,'e');
  return w;
}
/* Vienas mėlynas Vilkas; gestų judesiai lieka CSS, be skirtingų personažų suliejimo. */
var WOLF_POSES={raise:'/photos/vilkas_blue_pose.webp',bang:'/photos/vilkas_blue_pose.webp',welcome:'/photos/vilkas_blue_pose.webp',bow:'/photos/vilkas_blue_pose.webp',wink:'/photos/vilkas_blue_pose.webp',thumb:'/photos/vilkas_blue_pose.webp',coffee:'/photos/vilkas_blue_pose.webp',present:'/photos/vilkas_blue_pose.webp',clap:'/photos/vilkas_blue_pose.webp',spill:'/photos/vilkas_blue_pose.webp',glasses:'/photos/vilkas_blue_pose.webp',guitar:'/photos/vilkas_blue_pose.webp',guitar2:'/photos/vilkas_blue_pose.webp'};
var WOLF_POSES_ORIG={raise:'/photos/vilkas_raise.webp',bang:'/photos/vilkas_bang.webp',welcome:'/photos/vilkas_welcome.webp',bow:'/photos/vilkas_bow.webp',wink:'/photos/vilkas_wink.webp',thumb:'/photos/vilkas_thumb.webp',coffee:'/photos/vilkas_coffee.webp',present:'/photos/vilkas_present.webp',clap:'/photos/vilkas_clap.webp',spill:'/photos/vilkas_spill.webp',glasses:'/photos/vilkas_glasses.webp',guitar:'/photos/vilkas_guitar.webp',guitar2:'/photos/vilkas_guitar2.webp'};
try{ var _wvb=String(window.PAGE_BUILD||'1'); Object.keys(WOLF_POSES).forEach(function(k){ WOLF_POSES[k]+='?v='+_wvb; }); }catch(e){}
Object.keys(WOLF_POSES).forEach(function(k){ var i=new Image(); i.src=WOLF_POSES[k]; });
var wolfHideTimer=null;
var currentPose='raise', gestureTimer=null;
function setPose(p){
  var src=WOLF_POSES[p]||WOLF_POSES.raise;
  var a=document.getElementById('hostWolfImg'), b=document.getElementById('wolfPopImg'), g=document.getElementById('wolfPopGhost');
  if(a) a.src=src;
  /* has-video (anim) režime #wolfPopImg matomas TIK tyloje — ten visada p1 (ta pati apranga, užčiaupta burna).
     Pozų still'ai keičiami tik be animacijos (fallback), kad nebūtų smokingo/kostiumo mirgėjimo. */
  try{ var popHV=document.getElementById('wolfPop'); if(popHV && popHV.classList.contains('has-video')){ src=WOLF_POSES.raise; } }catch(e){}
  if(b && currentPose!==p && b.getAttribute('src')!==src){
    if(g){ g.src=b.src; restartClass(g,'fade'); }
    b.classList.remove('swap','swap-up'); void b.offsetWidth;
    b.src=src;
    b.classList.add(p==='raise'||p==='clap'||p==='glasses' ? 'swap-up' : 'swap');
  }
  currentPose=p;
}
function setBubble(title, speech){
  var t=document.getElementById('wolfBubT'), s=document.getElementById('wolfBubS');
  if(t && title!=null) t.textContent=title;
  if(s && speech!=null){
    s.innerHTML='';
    speech.split(/\s+/).filter(Boolean).forEach(function(w, i){
      var sp=document.createElement('span'); sp.textContent=(i?' ':'')+w; s.appendChild(sp);
    });
  }
  var b=document.getElementById('wolfPopBubble');
  if(b){
    var blank=!(t&&t.textContent) && !(s&&s.textContent);
    b.classList.toggle('blank', blank);
    if(!blank && speech!=null && speech) restartClass(b,'pop');
  }
}
function revealWords(frac){
  var s=document.getElementById('wolfBubS'); if(!s) return;
  var sp=s.children, total=0, i;
  for(i=0;i<sp.length;i++) total+=sp[i].textContent.length+1;
  var target=Math.min(1, frac+0.04)*total, acc=0;
  for(i=0;i<sp.length;i++){ acc+=sp[i].textContent.length+1; sp[i].classList.toggle('on', acc-((sp[i].textContent.length+1)*0.4)<=target); }
}
function setNoAudio(on){ var b=document.getElementById('wolfPopBubble'); if(b) b.classList.toggle('noaudio', !!on); }
var CLAP=['welcome','clap','welcome','clap','welcome','clap'];
function clapSound(){
  try{ var t=ac().currentTime; noiseBurst(t, 0.05, 0.55); noiseBurst(t+0.012, 0.03, 0.3); }catch(e){}
}
function startGestures(list, ms){
  stopGestures();
  if(!list || list.length<2) return;
  var i=0;
  var pop=document.getElementById('wolfPop'); if(pop) pop.classList.add('lean');
  if(list[0]==='clap') clapSound();
  gestureTimer=setInterval(function(){
    i=(i+1)%list.length; setPose(list[i]);
    if(list[i]==='clap') clapSound();
  }, Math.max(600, ms || (list.indexOf('clap')>=0 ? 600 : 1000)));
}
function fanfareIntro(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    for(var i=0;i<34;i++){
      var tt=t0+i*0.065;
      noiseBurst(tt, 0.05, 0.08+0.3*(i/34));
    }
    var boom=ctx.createOscillator(), bg=ctx.createGain();
    boom.type='sine'; boom.frequency.setValueAtTime(90,t0+2.2); boom.frequency.exponentialRampToValueAtTime(40,t0+2.9);
    bg.gain.setValueAtTime(0.0001,t0+2.2); bg.gain.linearRampToValueAtTime(0.6,t0+2.23); bg.gain.exponentialRampToValueAtTime(0.0001,t0+3.1);
    boom.connect(bg); bg.connect(ctx.destination); boom.start(t0+2.2); boom.stop(t0+3.2);
    var notes=[[2.25,.16,[392,494,587]],[2.45,.16,[392,494,587]],[2.65,.16,[392,494,587]],[2.85,1.1,[523,659,784,1047]]];
    notes.forEach(function(n){
      n[2].forEach(function(f){
        var o=ctx.createOscillator(), g=ctx.createGain(), lp=ctx.createBiquadFilter();
        o.type='sawtooth'; o.frequency.value=f; lp.type='lowpass'; lp.frequency.value=2400;
        var s=t0+n[0];
        g.gain.setValueAtTime(0.0001,s); g.gain.linearRampToValueAtTime(0.07,s+0.03); g.gain.setValueAtTime(0.07,s+n[1]*0.7); g.gain.exponentialRampToValueAtTime(0.0001,s+n[1]+0.15);
        o.connect(lp); lp.connect(g); g.connect(ctx.destination); o.start(s); o.stop(s+n[1]+0.2);
      });
    });
    setTimeout(function(){ try{ showCymbal(); }catch(e){} }, 2850);
  }catch(e){}
}
function teapotPourSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var o=ctx.createOscillator(), g=ctx.createGain();
    o.type='sine'; o.frequency.setValueAtTime(1900,t0); o.frequency.linearRampToValueAtTime(2300,t0+0.9);
    g.gain.setValueAtTime(0.0001,t0); g.gain.linearRampToValueAtTime(0.05,t0+0.3); g.gain.linearRampToValueAtTime(0.0001,t0+0.9);
    o.connect(g); g.connect(ctx.destination); o.start(t0); o.stop(t0+1);
    for(var i=0;i<26;i++){
      var tt=t0+1.0+i*0.07+Math.random()*0.03;
      var b=ctx.createOscillator(), bg=ctx.createGain();
      b.type='sine'; var f=300+Math.random()*500+i*18;
      b.frequency.setValueAtTime(f,tt); b.frequency.exponentialRampToValueAtTime(f*1.8,tt+0.05);
      bg.gain.setValueAtTime(0.0001,tt); bg.gain.linearRampToValueAtTime(0.09,tt+0.01); bg.gain.exponentialRampToValueAtTime(0.0001,tt+0.07);
      b.connect(bg); bg.connect(ctx.destination); b.start(tt); b.stop(tt+0.08);
    }
    setTimeout(coffeeSound, 900);
  }catch(e){}
}
function splashSound(){
  try{ var t=ac().currentTime; noiseBurst(t, 0.35, 0.6); noiseBurst(t+0.1, 0.25, 0.35); beep(300,0.25,'sine',0.15,0); beep(180,0.3,'sine',0.12,0.05); }catch(e){}
}
var coffeeActive=false, coffeeTimer=null;
var coffeeIntermissionLotId=null;
function showTable(on){
  var t=document.getElementById('wolfTable'); if(!t) return;
  if(on){ t.classList.remove('hide'); restartClass(t,'show'); }
  else if(t.classList.contains('show')){ t.classList.remove('show'); restartClass(t,'hide'); }
}
function startCoffee(){
  coffeeActive=true; showTable(true);
  setTimeout(teapotPourSound, 500);
  clearTimeout(coffeeTimer);
  /* Trumpai kava → tada dingsta į dūmus */
  coffeeTimer=setTimeout(function(){ endCoffee(); wolfPopHideSoon(200); }, 6500);
}
function startOpeningCoffee(ms){
  /* Po welcome: Vilkas geria kavą, MUZIKA groja, JOKIŲ komentarų ~2 min. */
  coffeeActive=true; showTable(true);
  try{ setTimeout(teapotPourSound, 400); }catch(e){}
  try{ setPose('coffee'); }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){ pop.classList.add('show','alive','coffee'); pop.classList.remove('talking','hide'); }
  }catch(e){}
  try{ setBubble('☕ Kavos pertraukėlė…', ''); }catch(e){}
  clearTimeout(coffeeTimer);
  coffeeTimer=setTimeout(function(){
    endCoffee();
    try{ if(vilkasStageOn) wolfPopShow('coffee'); }catch(e){}
  }, Math.max(60000, Number(ms)||120000));
}
function startIntermissionCoffee(lotId){
  coffeeIntermissionLotId=lotId;
  startCoffee();
}
function endCoffee(){
  coffeeActive=false; clearTimeout(coffeeTimer); showTable(false);
  var pop=document.getElementById('wolfPop'); if(pop) pop.classList.remove('coffee');
}
var nrHistory={};
function pickNR(key, arr){
  var h=nrHistory[key]||(nrHistory[key]=[]);
  var keep=Math.min(arr.length-1, Math.max(1, Math.floor(arr.length*0.6)));
  var pool=[]; for(var i=0;i<arr.length;i++){ if(h.indexOf(i)<0) pool.push(i); }
  var idx=pool.length ? pool[Math.floor(Math.random()*pool.length)] : Math.floor(Math.random()*arr.length);
  h.push(idx); while(h.length>keep) h.shift();
  return arr[idx];
}
function stopGestures(){
  clearInterval(gestureTimer); gestureTimer=null;
  var pop=document.getElementById('wolfPop'); if(pop) pop.classList.remove('lean');
}
function fxFloat(cls, txt, x, y, extra){
  var d=document.createElement('div');
  d.className='fx-float '+cls; d.textContent=txt;
  if(x!=null){ d.style.left=x+'px'; d.style.top=y+'px'; }
  if(extra) for(var k in extra) d.style.setProperty(k, extra[k]);
  document.body.appendChild(d);
  setTimeout(function(){ d.remove(); }, 2100);
}
function emojiBurst(list, n){
  var cx=innerWidth/2, cy=innerHeight*0.62;
  n=Math.min(n||8, 9);
  for(var i=0;i<n;i++){
    var ang=Math.random()*Math.PI*2, dist=120+Math.random()*200;
    fxFloat('fx-mini', list[i%list.length], cx-19, cy-19, {'--dx':Math.cos(ang)*dist+'px','--dy':(Math.sin(ang)*dist-120)+'px','--rot':(Math.random()*80-40)+'deg'});
  }
}
function heartBurst(){
  fxFloat('fx-bigheart','❤️');
  setTimeout(function(){ emojiBurst(['💖','💕','❤️','😘','💗'], 16); }, 250);
  try{ [660,880,1320].forEach(function(f,i){ beep(f,0.18,'sine',0.12,i*0.09); }); }catch(e){}
}
function splashBurst(){
  emojiBurst(['☕','💦','💧','😱','💦'], 16);
  splashSound();
}
function shutterSound(){
  if(!pageAllowsAudio() || !isAudioMaster()) return;
  try{
    var ctx=ac(), t0=ctx.currentTime, len=Math.floor(ctx.sampleRate*0.075);
    if(ctx.state==='suspended') ctx.resume().catch(function(e){ console.warn('Camera audio resume failed',e); });
    [0,0.085].forEach(function(offset){
      var buf=ctx.createBuffer(1,len,ctx.sampleRate), d=buf.getChannelData(0);
      for(var i=0;i<len;i++) d[i]=(Math.random()*2-1)*Math.pow(1-i/len,2);
      var src=ctx.createBufferSource(); src.buffer=buf;
      var hp=ctx.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=1800;
      var g=ctx.createGain(); g.gain.value=offset?0.12:0.22;
      src.connect(hp); hp.connect(g); g.connect(ctx.destination); src.start(t0+offset);
      src.stop(t0+offset+0.08);
    });
  }catch(e){ console.warn('Camera shutter audio failed',e); }
}
function entranceCrowdSound(){
  if(!pageAllowsAudio() || !isAudioMaster()) return;
  try{
    crowdOoohSound({duration:6,volume:0.12});
    applauseSound();
    setTimeout(function(){ if(pageAllowsAudio() && isAudioMaster()) applauseSound(); },2500);
  }catch(e){ console.warn('Wolf entrance crowd audio failed',e); }
}
function cameraFlashes(n, entrance){
  var pop=document.getElementById('wolfPop'); if(!pop) return;
  if(!isVilkasStageOn() || phoneAway) return;
  var angles=[-165,-135,-105,-75,-45,-20];
  var reduced=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  n=n||6;
  if(reduced) n=Math.min(n,3);
  if(entrance) entranceCrowdSound();
  for(var i=0;i<n;i++){ (function(k){
    setTimeout(function(){
      if(!isVilkasStageOn() || phoneAway) return;
      var r=pop.getBoundingClientRect();
      if(!r.width || r.top>innerHeight-20) return;
      var a=angles[Math.floor(Math.random()*angles.length)]*Math.PI/180;
      var cx=r.left+r.width/2, cy=r.top+r.height*0.35, dist=r.width*(0.55+Math.random()*0.4);
      var f=document.createElement('div'); f.className='cam-flash';
      if(entrance) f.style.setProperty('--flash-size','clamp(160px,32vw,440px)');
      f.style.left=(cx+Math.cos(a)*dist)+'px'; f.style.top=(cy+Math.sin(a)*dist)+'px';
      f.style.setProperty('--rot',(Math.random()*160-80)+'deg');
      document.body.appendChild(f); setTimeout(function(){ f.remove(); },reduced?1150:850);
      pop.classList.add('flash-hit'); setTimeout(function(){ pop.classList.remove('flash-hit'); },180);
      shutterSound();
    }, k*(reduced?850:420)+Math.random()*60);
  })(i); }
}
var welcomeWolfLots={}, welcomeWolfFirstLot=false;
function welcomeWolfForLot(lot){
  var id=lot && (lot.lot_id||lot.id);
  if(!id){ console.warn('Wolf entrance requires a lot id'); return false; }
  var key=String(id)+'@'+String(lot.starts_at||'');
  if(welcomeWolfLots[key]) return false;
  welcomeWolfLots[key]=true;
  var number=Number(lot.lot_number);
  var welcome=!welcomeWolfFirstLot || (number>0 && number%10===0);
  welcomeWolfFirstLot=true;
  if(!welcome) return false;
  cameraFlashes(18,true);
  return true;
}
function wolfPhotoMoment(caption, pose){
  var card=document.getElementById('wolfPhoto'), img=document.getElementById('wolfPhotoImg');
  var cap=document.getElementById('wolfPhotoCaption');
  if(!card || !img) return;
  img.src=WOLF_POSES[pose||currentPose]||WOLF_POSES.raise;
  if(cap) cap.textContent=(caption||'Vilkas scenoje')+' · +37066331913';
  card.classList.remove('show'); void card.offsetWidth; card.classList.add('show');
  setTimeout(function(){ card.classList.remove('show'); },8200);
}
function photographedWolf(caption, pose){
  cameraFlashes(3);
  setTimeout(function(){ wolfPhotoMoment(caption, pose); },520);
}
function cheerBurst(){
  emojiBurst(['🔥','👍','💪','🎉','⭐'], 14);
}
var LAUGH_LINES=[
  'Cha cha cha! Ha ha ha! Vilkas juokiasi!',
  'Ha ha ha! Cha cha! Oi, kaip juokinga!',
  'Ho ho ho! Cha-cha-cha! Man linksmiau nei jums!',
  'Ha ha ha ha! Cha cha! Kaina kyla — o aš juokiuosi!',
  'Cha cha cha! Ha! Šitas aukcionas — geriausias cirkas!',
  'Ha ha! Cha cha cha! Vilkas nesulaiko juoko!',
  'Ho-ho! Cha cha! Piniginės dreba — o aš juokiuosi!',
  'Ha ha ha! Cha! Dar vienas euras — ir aš vėl juoksiu!'
];
var SOLD_BAJER=[
  'Cha cha! Šitas lotas — į istoriją!',
  'Na taip — piniginė plonesnė, o šypsena platesnė!',
  'Vilkas ploja kojom! Tokia pergalė retai matoma!',
  'Bajeriukas: kas nespėjo — tas pavydės iki sekmadienio!',
  'Ir vėl — vienas laimingas, visi kiti — su istorija papasakoti!',
  'Ha ha! Kūjis ilsisi, o nugalėtojas — šypsosi!',
  'Kaip sako Vilkas: kas drįso — tas ir turi!',
  'Bajeriukas: telefonas naujose rankose, o aš — su nauju komplimentu!',
  'Cha cha! Net mano akiniai nusišypsojo!',
  'Kas pralošė — ateikit penktadienį; kas laimėjo — saugokit dėžutę!',
  'Vilkas sako: geriau vienas euro spaudimas negu šimtas „gal vėliau“!',
  'Bajeriukas: kaina pakilo greičiau nei mano uodega rytą!',
  'Ha ha ha! Salė ūžia, o aš jau galvoju apie kitą lotą!',
  'Šitas sandoris — kaip kava: stiprus ir be cukraus!',
  'Na taip — laimėtojas šypsosi, o aš plakamiu kūju orą iš džiaugsmo!',
  'Bajeriukas: jei būčiau bankas — duočiau kreditą už tokią drąsą!',
  'Cha cha! Istorija bus pasakojama prie stalo iki Kalėdų!',
  'Vilkas patvirtina: čia ne lošimas — čia charakterio egzaminas. Išlaikyta!'
];
var BID_BAJER=[
  'Bajeriukas: pirštas greitesnis už mintį!',
  'Cha cha — ir vėl kaina šoka!',
  'Vilkas mato: čia jau ne žaidimas, čia sportas!',
  'Piniginė sušuko „ai“, o širdis — „dar!“',
  'Kaip sako mano močiutė: kas kelia — tas ir turi!',
  'Bajeriukas: mygtukas raudonas ne veltui — kaip uoga!',
  'Na taip — ir vėl salė sujudėjo!',
  'Ha ha! Net kėdės girgžda iš susijaudinimo!',
  'Čia jau karšta kaip keptuvėj — tik be aliejaus!',
  'Bajeriukas: vienas euras — mažai, o emocija — didelė!',
  'Vilkas skaičiuoja: drąsa plius euras lygu pergalė!',
  'Hei, kas dar miega — keliatės, čia aukcionas, ne pietų miegas!'
];
var lastSingAt=0, sangFor={}, lastSmokeAt=0, wolfInSmoke=false, smokePuffTimer=null;
function clearSmoke(){
  wolfInSmoke=false;
  clearInterval(smokePuffTimer); smokePuffTimer=null;
  var field=document.getElementById('smokeField');
  if(!field) return;
  field.classList.remove('on');
  var puffs=field.querySelectorAll('.smoke-puff');
  for(var i=0;i<puffs.length;i++) puffs[i].remove();
}
function puffSmoke(n){
  var field=document.getElementById('smokeField');
  if(!field) return;
  n=n==null?(3+Math.floor(Math.random()*3)):n;
  for(var i=0;i<n;i++){
    var p=document.createElement('div');
    p.className='smoke-puff';
    /* Dešinėje apačioje — kur Vilkas dingsta */
    p.style.left='auto';
    p.style.right=(2+Math.random()*28)+'%';
    p.style.bottom=(2+Math.random()*22)+'%';
    p.style.setProperty('--sx',(Math.random()*100-50)+'px');
    p.style.setProperty('--sz',(140+Math.random()*160)+'px');
    p.style.setProperty('--dur',(5.5+Math.random()*3)+'s');
    p.style.animationDelay=(i*0.2+Math.random()*0.25)+'s';
    field.appendChild(p);
    (function(el){ setTimeout(function(){ if(el&&el.parentNode) el.remove(); }, 9500); })(p);
  }
  lastSmokeAt=Date.now();
}
function enterSmokeBreak(){
  if(announceBusy || announceQueue.length || coffeeActive) return;
  wolfInSmoke=true;
  var field=document.getElementById('smokeField');
  if(field) field.classList.add('on');
  puffSmoke(5);
  clearInterval(smokePuffTimer);
  smokePuffTimer=setInterval(function(){
    if(!wolfInSmoke || announceBusy || announceQueue.length) return;
    puffSmoke(2+Math.floor(Math.random()*2));
  }, 3200);
}
function watchAmbienceSmoke(){
  /* Dūmai tik kai Vilkas dingęs — ne maišosi su juo scenoje */
  if(!wolfInSmoke) return;
  if(announceBusy || announceQueue.length) return;
  if(Date.now()-lastSmokeAt<2800) return;
  puffSmoke(2);
}
function wolfLaughSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime+0.04;
    /* Cha-cha-cha tipo juokas — trumpi „ha“ tonai */
    var bursts=[0,0.16,0.32, 0.55,0.70,0.85, 1.15,1.30,1.48, 1.85,2.00];
    bursts.forEach(function(off,i){
      var t=t0+off;
      var o=ctx.createOscillator(), g=ctx.createGain();
      o.type='sawtooth';
      var f=220+(i%3)*40+Math.random()*25;
      o.frequency.setValueAtTime(f,t);
      o.frequency.exponentialRampToValueAtTime(f*0.75,t+0.11);
      g.gain.setValueAtTime(0.0001,t);
      g.gain.exponentialRampToValueAtTime(0.22,t+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001,t+0.12);
      o.connect(g); g.connect(ctx.destination);
      o.start(t); o.stop(t+0.14);
      if(i%3===0) noiseBurst(t, 0.04, 0.15);
    });
  }catch(e){}
}
function laughBurst(){ emojiBurst(['😄','😂','🤣','😆','🐺'], 14); }
function notesBurst(){ emojiBurst(['🎵','🎶','💃','🕺','🎵'], 16); }
function rockBurst(){ emojiBurst(['🎸','🤘','⚡','🔥','🎶'], 18); }
function maybeSing(key, prob){
  // Aukciono vedėjas nepertraukia prekybos dainelėmis ar bajeriukais.
  return false;
}
/* Bajeriukai generuojami tik tada, kai Vilkas juos iš tiesų pasako. */
function coffeeSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var n=Math.floor(ctx.sampleRate*1.6), buf=ctx.createBuffer(1,n,ctx.sampleRate), d=buf.getChannelData(0);
    for(var i=0;i<n;i++) d[i]=(Math.random()*2-1)*0.6;
    var src=ctx.createBufferSource(); src.buffer=buf;
    var bp=ctx.createBiquadFilter(); bp.type='bandpass'; bp.Q.value=4;
    bp.frequency.setValueAtTime(500,t0); bp.frequency.exponentialRampToValueAtTime(1800,t0+1.5);
    var g=ctx.createGain(); g.gain.setValueAtTime(0.001,t0); g.gain.linearRampToValueAtTime(0.35,t0+0.1); g.gain.setValueAtTime(0.35,t0+1.3); g.gain.linearRampToValueAtTime(0.001,t0+1.6);
    src.connect(bp); bp.connect(g); g.connect(ctx.destination); src.start(t0); src.stop(t0+1.6);
    [2.1,2.35].forEach(function(t){ noiseBurst(t0+t, 0.12, 0.25); });
  }catch(e){}
}
function restartClass(el, cls){ if(!el) return; el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); }
function wolfPopShow(pose){
  if(typeof isVilkasStageOn==='function' && !isVilkasStageOn()) return;
  clearTimeout(wolfHideTimer);
  clearSmoke(); /* Vilkas grįžta — dūmai dingsta */
  var pop=document.getElementById('wolfPop');
  setPose(pose||'raise');
  if(!pop) return;
  pop.classList.remove('idle','hide');
  pop.classList.add('alive');
  if(!pop.classList.contains('show')){ restartClass(pop,'show'); }
  else { pop.classList.add('show'); }
  pop.classList.add('alive');
  /* Gyvas klipas kaip sokejos — telefonas/bajeriai/TTS lieka per announceQueue */
  try{ keepVilkasVideoAlive(); }catch(e){}
}
function wolfPopTalking(on){
  var pop=document.getElementById('wolfPop');
  if(pop) pop.classList.toggle('talking', !!on);
  /* Baigus kalbą has-video režime po animacija lieka matomas still — grąžinam į p1 (ta pati apranga, užčiaupta burna) */
  if(pop && !on && pop.classList.contains('has-video')){ try{ setPose('raise'); }catch(e){} }
}
function wolfPopHideSoon(ms){
  /* F9 scenoje Vilkas LIEKA — tik burbulas užsidaro. Kitaip telefonas mato lotą be vedėjo. */
  if(typeof isVilkasStageOn==='function' && isVilkasStageOn()){
    clearTimeout(wolfHideTimer);
    wolfHideTimer=setTimeout(function(){
      setBubble('', '');
      var b=document.getElementById('wolfPopBubble');
      if(b) b.classList.remove('open');
      wolfPopTalking(false);
      wolfPopShow(currentPose||'raise');
    }, ms||900);
    return;
  }
  clearTimeout(wolfHideTimer);
  wolfHideTimer=setTimeout(function(){
    if(announceBusy || announceQueue.length || coffeeActive) return;
    var pop=document.getElementById('wolfPop');
    if(!pop) return;
    pop.classList.remove('talking','lean','coffee','side','idle','alive');
    pop.classList.add('show');
    restartClass(pop,'hide');
    setBubble('', '');
    var b=document.getElementById('wolfPopBubble');
    if(b) b.classList.remove('open');
    enterSmokeBreak();
    setTimeout(function(){
      if(announceBusy || announceQueue.length) return;
      if(typeof isVilkasStageOn==='function' && isVilkasStageOn()){ wolfPopShow('raise'); return; }
      pop.classList.remove('show','hide','alive');
    }, 650);
  }, ms||900);
}
function keepVilkasVideoAlive(){
  /* Skaidrus anim WebP (be fono) — F9 scenoje visada matomas + disco judesiai. */
  if(typeof isVilkasStageOn!=='function' || !isVilkasStageOn()) return;
  if(document.visibilityState==='hidden') return;
  try{
    var pop=document.getElementById('wolfPop');
    var vid=document.getElementById('wolfPopVid');
    if(!vid||!pop) return;
    if(!pop.classList.contains('show')) return;
    if(vid.tagName==='VIDEO'){
      vid.muted=true; vid.defaultMuted=true; vid.loop=true; vid.playsInline=true;
      vid.setAttribute('playsinline',''); vid.setAttribute('muted','');
      if(vid.error){ pop.classList.remove('has-video'); return; }
      pop.classList.add('has-video');
      if(vid.paused || vid.ended){
        var p=vid.play();
        if(p&&p.catch) p.catch(function(){ try{ pop.classList.remove('has-video'); }catch(e){} });
      }
      return;
    }
    /* IMG anim WebP — jokio juodo remo; tik vilkas */
    if(!vid.getAttribute('src') && !vid.src){ pop.classList.remove('has-video'); return; }
    if(!vid.complete || vid.naturalWidth===0){ pop.classList.remove('has-video'); return; }
    pop.classList.add('has-video');
  }catch(e){}
}
function keepVilkasOnStage(){
  if(typeof isVilkasStageOn==='function' && isVilkasStageOn()){
    if(phoneAway){
      /* F11 telefono išėjimas — NErodyti Vilko, kol negrįžo */
      try{
        var pop=document.getElementById('wolfPop');
        if(pop){ pop.classList.remove('show','alive','talking'); pop.classList.add('hide'); }
      }catch(e){}
      return;
    }
    try{ wolfPopShow(currentPose||'raise'); }catch(e){}
    try{ keepVilkasVideoAlive(); }catch(e){}
    return;
  }
  try{
    var vid=document.getElementById('wolfPopVid');
    if(vid && vid.tagName==='VIDEO' && !vid.paused) vid.pause();
  }catch(e){}
  var pop=document.getElementById('wolfPop');
  if(pop){
    pop.classList.remove('show','alive','talking','hide','has-video');
  }
}
var IDLE_POSES=['raise','welcome','thumb','present','clap','wink','glasses','raise'];
var idlePoseI=0;
setInterval(keepVilkasOnStage, 900);
setInterval(keepVilkasVideoAlive, 900);
setInterval(function(){
  if(typeof isVilkasStageOn!=='function' || !isVilkasStageOn()) return;
  if(announceBusy || (announceQueue&&announceQueue.length) || phoneCallActive || hostAudio) return;
  idlePoseI=(idlePoseI+1)%IDLE_POSES.length;
  try{
    var popV=document.getElementById('wolfPop');
    /* has-video: tyloje matomas p1 kadras — laikom VIENĄ pozą (be smokingo/kostiumo mirgėjimo), gyvumas per soft-sway */
    if(popV && popV.classList.contains('has-video')) setPose('raise'); else setPose(IDLE_POSES[idlePoseI]);
  }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(!pop) return;
    pop.classList.remove('lean','strike','surprise');
    if(idlePoseI%3===0) pop.classList.add('lean');
  }catch(e){}
}, 4200);
function hammerStrike(){
  setPose('bang');
  hammerSound();
  restartClass(document.getElementById('wolfPop'),'strike');
  restartClass(document.getElementById('wolfImpact'),'go');
  restartClass(document.getElementById('stageRoot'),'shake');
  restartClass(document.getElementById('hostBar'),'host-flash');
}
function bangHammer(times, onDone, gongLast){
  if(times===0){ if(onDone) setTimeout(onDone, 50); return; }
  times=times||1;
  var i=0;
  (function next(){
    setPose('raise');
    setTimeout(function(){
      hammerStrike();
      /* Plaktuko smūgis, po ~55ms — gongo skambesys */
      if(gongLast && i===times-1) setTimeout(function(){ try{ gongSound(); }catch(e){} }, 55);
      i++;
      if(i<times){ setTimeout(next, 330); }
      else if(onDone){ setTimeout(onDone, gongLast ? 520 : 380); }
    }, 170);
  })();
}
function wolfGesture(kind){
  var w=document.getElementById('hostWolf');
  if(!w) return;
  w.classList.remove('idle','talking','bow','wave');
  void w.offsetWidth;
  if(kind==='talk'){ w.classList.add('talking'); return; }
  if(kind==='bow'){ w.classList.add('bow'); setTimeout(function(){ if(!announceBusy){ w.classList.remove('bow'); w.classList.add('idle'); } }, 1100); return; }
  if(kind==='wave'){ w.classList.add('wave'); setTimeout(function(){ if(!announceBusy){ w.classList.remove('wave'); w.classList.add('idle'); } }, 900); return; }
  w.classList.add('idle');
}
function wolfIdle(){
  var w=document.getElementById('hostWolf');
  if(!w) return;
  w.classList.remove('talking','bow','wave');
  w.classList.add('idle');
}
wolfIdle();
function speechTitle(t){ return String(t||'').replace(/\b\d+\s?(GB|TB)\b/ig,'').replace(/\s{2,}/g,' ').trim(); }
function tonightTitles(){
  var titles=[], seen={};
  function add(t){
    t=speechTitle(t);
    if(!t || seen[t]) return;
    seen[t]=1; titles.push(t);
  }
  if(state && state.lot && state.lot.status==='live') add(state.lot.title);
  ((state && state.queue)||[]).forEach(function(q){ if(titles.length<10) add(q.title); });
  if(!titles.length) ((state && state.queue_titles)||[]).forEach(function(t){ if(titles.length<10) add(t); });
  return titles;
}
function openingLines(){
  var titles=tonightTitles();
  var items;
  if(!titles.length) items='keletas išmaniųjų telefonų ir kitų gerų daiktų';
  else if(titles.length>5) items=titles.slice(0,5).join(', ')+' ir dar keletas įdomių daiktų';
  else if(titles.length>1) items=titles.slice(0,-1).join(', ')+' ir '+titles[titles.length-1];
  else items=titles[0];
  return [
    'Labas vakaras, susirinkusieji! Malonu jus matyti. Sveikinu jus Penktadienio aukcione. Įsitaisykite patogiai.',
    'Taisyklės paprastos. Kiekviena prekė startuoja nuo simbolinės kainos. Vienas paspaudimas — ir kaina kyla vienu euru. Laimi tas, kurio statymas lieka paskutinis, kai nuskamba mano gongas.',
    'Gongas! Lotas uždarytas!',
    'Šį vakarą ant stalo, eilės tvarka: '+items+'. Apačioje galite juos peržiūrėti. Atsipalaiduokite… ir stebėkite!'
  ];
}
var openingDone = (Date.now()-(parseInt(sessionStorage.getItem('vilkas_open'),10)||0)) < 10*60*1000;
if(/[?&]fresh=(?:\d+|play|demo)(?:&|$)/.test(location.search)){ openingDone=false; try{ sessionStorage.removeItem('vilkas_open'); }catch(e){} }
function maybeOpeningSpeech(){
  // DISABLED: server director owns this
  return;
  if(openingDone || !voiceOn) return;
  /* Palaukti kol state ateis — kad Vilkas vardytų tikras prekes iš navigacijos */
  if(!state) return;
  var titles=tonightTitles();
  if(state.auction_locked && !titles.length) return;
  openingDone=true;
  try{ sessionStorage.setItem('vilkas_open', String(Date.now())); }catch(e){}
  var L=openingLines();
  Promise.all([
    Promise.resolve(L[0]),
    Promise.resolve(L[1]),
    Promise.resolve(L[2]),
    vilkasThink('opening_items', {tonight_titles:titles, items:titles.join(', ')}, L[3])
  ]).then(function(lines){
    lines.forEach(prefetchTts);
    queueAnnounce(lines[0], {pose:'welcome', bangs:0, gestures:['welcome','present','raise'], gestureMs:1600, bubble:'Penktadienio aukcionas'});
    queueAnnounce(lines[1], {pose:'present', bangs:0, gestures:['present','welcome','thumb'], gestureMs:1800, bubble:'Taisyklės'});
    queueAnnounce(lines[2], {pose:'bang', bangs:0, gestures:['bang','raise'], gestureMs:900, bubble:'🔔 Gongas!',
      onSpeak:function(){
        setTimeout(function(){ try{ hitGong(); }catch(e){} }, 2400);
      }});
    queueAnnounce(lines[3], {pose:'present', bangs:1, after:'bow', gestures:['present','raise','welcome'], gestureMs:1600, bubble:'Šio vakaro prekės'});
  });
}
function setHostBubble(html){
  var b=document.getElementById('hostBubble');
  if(!b) return;
  b.innerHTML=html;
  b.classList.remove('talk');
  void b.offsetWidth;
  b.classList.add('talk');
}
function eurosWords(n){
  var x=Math.round(Number(n)||0);
  if(x>0 && x<1000){
    var U=['','vieną','du','tris','keturis','penkis','šešis','septynis','aštuonis','devynis'];
    var T=['dešimt','vienuolika','dvylika','trylika','keturiolika','penkiolika','šešiolika','septyniolika','aštuoniolika','devyniolika'];
    var D=['','','dvidešimt','trisdešimt','keturiasdešimt','penkiasdešimt','šešiasdešimt','septyniasdešimt','aštuoniasdešimt','devyniasdešimt'];
    var w=[], h=Math.floor(x/100), r=x%100;
    if(h===1) w.push('šimtą'); else if(h>1) w.push((h===2?'du':U[h])+' šimtus');
    if(r>=10 && r<20) w.push(T[r-10]);
    else { if(r>=20) w.push(D[Math.floor(r/10)]); if(r%10) w.push(U[r%10]); }
    var last=x%10, teen=(r>=10&&r<20);
    return w.join(' ')+' '+(teen||last===0 ? 'eurų' : (last===1 ? 'eurą' : 'eurus'));
  }
  return x+' eurų';
}
function pick(a){ return a[Math.floor(Math.random()*a.length)]; }
function capSentences(s){ return s.replace(/(^|[!?.]\s+)([a-ząčęėįšųūž])/g, function(m,a,b){ return a+b.toUpperCase(); }); }
/* Vilkas smegenys — LLM + šablonai ant GPU kompo (be ElevenLabs) */
function vilkasThink(event, payload, fallbackText){
  var fb=String(fallbackText||'').trim()||'Nestabdom, judam! Kas kitas?';
  return fetch('/api/vilkas/think', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({event:event, payload:payload||{}})
  })
  .then(function(r){ return r.ok ? r.json() : {text:fb}; })
  .then(function(j){ return (j && j.text) ? String(j.text).trim() : fb; })
  .catch(function(){ return fb; });
}
function bidLine(name, amount, isFirst){
  var n=String(name||'').split(' ')[0]||'drauge';
  var priceNow=eurosWords(amount);
  var item='telefono';
  try{
    var t=(state && state.lot && state.lot.title) ? String(state.lot.title) : '';
    if(/iphone|apple/i.test(t)) item='iPhone';
    else if(/samsung|galaxy/i.test(t)) item='Samsung';
    else if(/nokia|lumia/i.test(t)) item='Nokia';
    else if(/motorola|moto/i.test(t)) item='Motorola';
    else if(/telefon/i.test(t)) item='telefono';
  }catch(e){}
  var fem=false;
  try{ fem=!!isFemaleName(name); }catch(eF){}
  var praise=fem ? 'šaunuolė, šaunuolė' : 'šaunuolis, šaunuolis';
  var want=fem ? 'Nori '+item+'?' : 'Nori '+item+'?';
  /* Gyvas Vilko stilius su keliančiu žmogumi — mokykla tobulina bajeriukus. */
  return pickNR('bidSpeechLive',[
    'O '+n+' pakėlė — '+praise+'! '+want+' Viso jau '+priceNow+'. Kas kitas?',
    'Žiūrėkit — '+n+' kelia! '+praise+'! '+want+' Dabar '+priceNow+'. Kas atsakys?',
    'Ooo, '+n+'! '+praise+'! Pakėlė kainą — '+want+' Jau '+priceNow+'. Kas perims?',
    'Štai '+n+' spaudžia! '+praise+'! Gal tikrai nori '+item+'? '+priceNow+'. Kas kitas?',
    'Nu va — '+n+' pakėlė! '+praise+'! '+want+' Kaina '+priceNow+'. Nestabdom!',
    'Brawo, '+n+'! '+praise+'! '+item+' jau '+priceNow+'. Kas drįsta atsakyti?'
  ]);
}
function bidLineRaw(name, amount, isFirst){ return bidLine(name, amount, isFirst); }
function bidPose(name){ return isFemaleName(name) ? pickNR('fpose',['wink','glasses']) : pickNR('mpose',['thumb','raise','clap']); }
var hostAudio = null;
var speakGen = 0; /* kiekviena nauja kalba — senos Async TTS / onended miršta */
function interruptAllSpeech(){
  speakGen++;
  announceEpoch++;
  try{ clearTimeout(visualAnnTimer); visualAnnTimer=null; }catch(eVA){}
  announceBusy=false;
  announceCurrentJob=null;
  announceQueue=[];
  setPhoneCallActive(false);
  phoneSessionActive=false;
  phoneAway=false;
  try{ clearTimeout(phoneAwayTimer); phoneAwayTimer=null; }catch(ePA){}
  phoneBidHold=[];
  try{ stopGuitarRiff(); }catch(e){}
  try{ if(coffeeActive) endCoffee(); }catch(e){}
  try{ if(hostAudio){ killAudio(hostAudio); hostAudio=null; } }catch(e){}
  try{ clearTimeout(gongTimer); gongTimer=null; }catch(e){}
  try{ if(gongAudio){ gongAudio.pause(); gongAudio.currentTime=0; gongAudio=null; } }catch(e){}
  try{ if(phoneRingAudio){ phoneRingAudio.pause(); phoneRingAudio.currentTime=0; phoneRingAudio=null; } }catch(e){}
  try{ clearTimeout(phoneTradeTimer); clearTimeout(phoneSpeechTimer); phoneSpeechTimer=null; }catch(e){}
  try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e){}
  try{ if(window.speechSynthesis) speechSynthesis.cancel(); }catch(e){}
  try{ stopGestures(); }catch(e){}
}
/*
  Statymo pranešimas negali laukti ElevenLabs užklausos: gongas ir frazė
  paleidžiami tą pačią akimirką naršyklėje. Tai ypač svarbu po žmogaus
  paspaudimo, kai garso leidimas jau suteiktas.
*/
var lastBidSpeechAt=0;
function announceJobProtected(job){
  if(!job) return false;
  if(job.tag==='sold' || job.tag==='start') return true;
  if(job.tag==='phone' || job.tag==='phone_catchup') return true;
  if(job.after==='bow' || job.pose==='bow') return true;
  return false;
}
function announceQueueHasProtected(){
  for(var i=0;i<announceQueue.length;i++){
    if(announceJobProtected(announceQueue[i])) return true;
  }
  return false;
}
function announceQueueSoftOnly(){
  if(!announceQueue.length) return true;
  for(var i=0;i<announceQueue.length;i++){
    var j=announceQueue[i];
    if(!j) continue;
    if(announceJobProtected(j)) return false;
    if(j.tag && j.tag!=='nudge' && j.tag!=='joke' && j.tag!=='phone' && j.tag!=='guitar' && j.tag!=='sing') return false;
  }
  return true;
}
function speakBidNow(name, amount){
  /* F11 / telefonas — JOKIŲ komentarų; vardai catchup po skambučio. */
  if(isPhoneBusy()){ holdBidDuringPhone(name, amount); return; }
  var now=Date.now();
  var bubble='🔔 '+name+' → '+Math.round(amount)+' €';
  var fallback=bidLine(name, amount, false);
  /* Gongas + burbulas VISADA iškart — balsas eina per eilę, be chaotiško pertraukimo. */
  try{ hitGong(); }catch(e){}
  try{ cheerBurst(); }catch(e){}
  try{ setBubble(bubble, fallback); }catch(e){}
  if(now-lastBidSpeechAt<9000) return;
  lastBidSpeechAt=now;
  /* Visada su vardu — bajeriukas / pagyrimas keliančiam. */
  var text=fallback || bidLine(name, amount, false);
  var fem=false; try{ fem=!!isFemaleName(name); }catch(eF){}
  var opts={
    tag:'bid', priority:true, pose:'bang', bangs:0, fast:!fem, fx:'cheer',
    gestures:['bang',bidPose(name),'thumb'], gestureMs:350, bubble:bubble
  };
  if(fem) opts.speed=0.88;
  /* Sold/start (arba einanti kalba) — nešluojam eilės; bid į frontą. Soft (nudge/joke/phone) — galima interrupt. */
  if(announceBusy || announceQueueHasProtected() || !announceQueueSoftOnly()){
    queueAnnounce(text, opts);
    return;
  }
  interruptAllSpeech();
  queueAnnounce(text, opts);
}
function readingMs(text){ return Math.max(1800, text.split(/\s+/).length*320); }
function silentRead(text, onDone, already){
  setNoAudio(true);
  setTimeout(function(){ if(onDone) onDone(); }, Math.max(600, readingMs(text)-(already||0)));
}
function speakHostBrowser(text, onDone, already){
  if(!ltVoice) ltVoice=pickLtVoice();
  if(!window.speechSynthesis || !ltVoice){ silentRead(text, onDone, already); return; }
  try{
    speechSynthesis.cancel();
    var u=new SpeechSynthesisUtterance(text);
    u.lang='lt-LT';
    u.rate=1.05;
    u.pitch=1.12;
    u.volume=1;
    u.voice=ltVoice;
    setNoAudio(true);
    u.onend=function(){ if(onDone) onDone(); };
    u.onerror=function(){ if(onDone) onDone(); };
    speechSynthesis.speak(u);
  }catch(e){ if(onDone) onDone(); }
}
function killAudio(a){
  try{
    a.onended=a.onerror=a.onplaying=a.ontimeupdate=null;
    if(a._wolfVoiceSource) a._wolfVoiceSource.disconnect();
    if(a._wolfVoiceGain) a._wolfVoiceGain.disconnect();
    a.pause(); a.removeAttribute('src'); a.load();
  }catch(e){}
}
/* TTS blob cache — NAUJAS_v3_lt (v3lt55). Senų kešų URL nebegalioja. */
var TTS_VER='v8-lt-intonacija-sexy-20261010';
var ttsBlobCache={}, ttsBlobWait={};
/*
  Vienas puslapio atidarymas negali generuoti dešimčių nepanaudojamų
  bajeriukų. TTS kvota naudojama tik frazei, kuri iš tiesų bus pasakyta.
*/
var TTS_PREFETCH_ENABLED = true;
function ttsCacheKey(text, fast, speed){
  var sp=(speed && speed>0)?String(speed):'';
  return TTS_VER+'|'+(fast?'1|':'0|')+sp+'|'+String(text||'');
}
function ttsFetchUrl(text, fast, speed){
  var u='/api/tts?text='+encodeURIComponent(text)+(fast?'&fast=1':'')+'&v='+encodeURIComponent(TTS_VER)+'&_='+Date.now();
  if(speed && speed>0) u+='&speed='+encodeURIComponent(String(speed));
  return u;
}
function prefetchTts(text, fast, speed){
  if(!TTS_PREFETCH_ENABLED) return;
  if(!voiceOn || !text) return;
  var key=ttsCacheKey(text, !!fast, speed);
  if(ttsBlobCache[key] || ttsBlobWait[key]) return;
  ttsBlobWait[key]=true;
  fetch(ttsFetchUrl(text, fast, speed), {cache:'no-store'})
    .then(function(r){ if(!r.ok) throw new Error('tts'); return r.blob(); })
    .then(function(b){ ttsBlobCache[key]=URL.createObjectURL(b); })
    .catch(function(){})
    .then(function(){ delete ttsBlobWait[key]; });
}
function loadTtsUrl(text, fast, speed){
  var key=ttsCacheKey(text, !!fast, speed);
  if(ttsBlobCache[key]) return Promise.resolve(ttsBlobCache[key]);
  if(!TTS_PREFETCH_ENABLED){
    return fetch(ttsFetchUrl(text, fast, speed), {cache:'no-store'})
      .then(function(r){ if(!r.ok) throw new Error('tts'); return r.blob(); })
      .then(function(b){ var u=URL.createObjectURL(b); ttsBlobCache[key]=u; return u; });
  }
  return new Promise(function(resolve, reject){
    var tries=0;
    (function poll(){
      if(ttsBlobCache[key]) return resolve(ttsBlobCache[key]);
      if(!ttsBlobWait[key] && tries===0) prefetchTts(text, fast, speed);
      tries++;
      if(tries>200) return reject(new Error('tts_timeout'));
      setTimeout(poll, 50);
    })();
  }).catch(function(){
    return fetch(ttsFetchUrl(text, fast, speed), {cache:'no-store'})
      .then(function(r){ if(!r.ok) throw new Error('tts'); return r.blob(); })
      .then(function(b){ var u=URL.createObjectURL(b); ttsBlobCache[key]=u; return u; });
  });
}
function speakHost(text, onDone, onStart, opts){
  opts = opts || {};
  var title = opts.bubble != null ? opts.bubble : null;
  var fast = !!opts.fast;
  var speed = (opts.speed && opts.speed>0) ? opts.speed : null;
  var readyUrl = opts.audioUrl || null;
  var myGen = (opts.gen != null) ? opts.gen : speakGen;
  function stillMine(){ return myGen === speakGen; }
  setNoAudio(false);
  var t0=Date.now(), done=false, startedCb=false, raf=null, tries=0;
  function begin(){
    if(!stillMine()) return;
    if(startedCb) return; startedCb=true;
    setBubble(title, text);
    var b=document.getElementById('wolfPopBubble');
    if(b){ b.classList.add('open'); restartClass(b,'pop'); }
    revealWords(0);
    wolfPopTalking(true);
    wolfGesture('talk');
    if(onStart) try{ onStart(); }catch(e){}
  }
  function finish(){
    if(done) return;
    done=true;
    clearTimeout(lateTimer);
    if(raf) cancelAnimationFrame(raf);
    if(a) killAudio(a);
    if(hostAudio===a) hostAudio=null;
    if(!stillMine()) return; /* perėmė naujas balsas — nekviesk onDone */
    revealWords(1);
    wolfIdle();
    wolfPopTalking(false);
    var b=document.getElementById('wolfPopBubble');
    if(b) b.classList.remove('open');
    setMusicDuck(false);
    if(onDone) onDone();
  }
  function fallback(blocked){
    if(done || !stillMine()) return;
    if(tries < 2){
      tries++;
      clearTimeout(lateTimer);
      if(a) killAudio(a);
      readyUrl=null;
      playOnce();
      return;
    }
    clearTimeout(lateTimer);
    if(a) killAudio(a);
    begin();
    silentRead(text, finish, Date.now()-t0);
  }
  var a=null, lateTimer=null;
  if(!voiceOn || !isAudioMaster() || !pageAllowsAudio()){ begin(); silentRead(text, finish); return; }
  if(!stillMine()) return;
  setMusicDuck(true);
  try{ if(hostAudio) killAudio(hostAudio); hostAudio=null; }catch(e){}
  try{ if(window.speechSynthesis) speechSynthesis.cancel(); }catch(e){}
  function bindAndPlay(url){
    if(!stillMine() || done) return;
    a = new Audio(url);
    a.preload = 'auto';
    a.volume = WOLF_VOICE_VOL;
    try{
      var VoiceAudioContext=window.AudioContext||window.webkitAudioContext;
      if(VoiceAudioContext){
        if(!wolfVoiceAudioContext) wolfVoiceAudioContext=new VoiceAudioContext();
        a._wolfVoiceSource=wolfVoiceAudioContext.createMediaElementSource(a);
        a._wolfVoiceGain=wolfVoiceAudioContext.createGain();
        a._wolfVoiceGain.gain.value=WOLF_VOICE_BOOST;
        a._wolfVoiceSource.connect(a._wolfVoiceGain);
        a._wolfVoiceEchoDelay=wolfVoiceAudioContext.createDelay(1);
        a._wolfVoiceEchoDelay.delayTime.value=WOLF_ECHO_DELAY_S;
        a._wolfVoiceEchoGain=wolfVoiceAudioContext.createGain();
        a._wolfVoiceEchoGain.gain.value=WOLF_ECHO_GAIN;
        a._wolfVoiceGain.connect(wolfVoiceAudioContext.destination);
        a._wolfVoiceGain.connect(a._wolfVoiceEchoDelay);
        a._wolfVoiceEchoDelay.connect(a._wolfVoiceEchoGain);
        a._wolfVoiceEchoGain.connect(wolfVoiceAudioContext.destination);
        if(wolfVoiceAudioContext.state==='suspended') wolfVoiceAudioContext.resume();
      } else {
        a.volume=Math.min(1,WOLF_VOICE_VOL*WOLF_VOICE_BOOST);
      }
    }catch(voiceGainError){
      a.volume=Math.min(1,WOLF_VOICE_VOL*WOLF_VOICE_BOOST);
      console.warn('Vilko balso stiprinimas nepavyko:',voiceGainError);
    }
    a.playbackRate = 0.93;
    if('preservesPitch' in a) a.preservesPitch = false;
    else if('webkitPreservesPitch' in a) a.webkitPreservesPitch = false;
    hostAudio = a;
    var started = false;
    lateTimer = setTimeout(function(){ if(!started && stillMine()) fallback(false); }, 12000);
    function startSync(){
      if(!stillMine() || started) return;
      started = true;
      clearTimeout(lateTimer);
      begin();
      (function loop(){
        if(done || !stillMine()) return;
        if(a && a.duration && isFinite(a.duration) && a.duration > 0){
          revealWords(a.currentTime / a.duration);
        }
        raf = requestAnimationFrame(loop);
      })();
    }
    a.onplaying = startSync;
    a.onended = finish;
    a.onerror = function(){ if(stillMine()) fallback(false); };
    var p = a.play();
    if(p && p.catch) p.catch(function(err){ if(stillMine()) fallback(err && err.name === 'NotAllowedError'); });
  }
  function playOnce(){
    if(!stillMine() || done) return;
    if(readyUrl){ bindAndPlay(readyUrl); readyUrl=null; return; }
    loadTtsUrl(text, fast, speed).then(function(url){
      if(!stillMine() || done) return;
      bindAndPlay(url);
    }).catch(function(){ if(stillMine()) fallback(false); });
  }
  playOnce();
}
function announceJobKey(job){
  if(!job) return '';
  return String(job.tag||'')+'|'+String(job.text||'').trim();
}
function runAnnounceQueue(){
  if(!pageAllowsAudio()){
    /* Hidden tab — eilė miršta, be fono TTS / Vilko. */
    announceQueue=[];
    announceBusy=false;
    announceCurrentJob=null;
    return;
  }
  if(!isCoverMode() && !isAudioMaster()){
    announceQueue=[];
    announceBusy=false;
    announceCurrentJob=null;
    return;
  }
  if(announceBusy || !announceQueue.length) return;
  /* Statymo pranešimas / skambučio vėliava — palaukiam. BET jei phoneCallActive
     užstrigo be hostAudio >3s, nenužudom eilės amžiams (F11 tada „neskamba“). */
  if(hostAudio){
    setTimeout(runAnnounceQueue, 180);
    return;
  }
  /* phoneCallActive stabdo KITUS darbus per skambučio skambėjimą.
     phone / phone_catchup — PRIVALO eiti (F11 „Atsiprašau“ / Alio / viršininkas).
     Kitaip: skambutis skamba, o Vilkas tyli amžinai. */
  if(phoneCallActive){
    var peek=announceQueue[0];
    var phoneJob=peek && (peek.tag==='phone' || peek.tag==='phone_catchup');
    if(phoneJob){
      setPhoneCallActive(false);
    } else if(phoneCallSince && Date.now()-phoneCallSince>3000){
      setPhoneCallActive(false);
    } else {
      setTimeout(runAnnounceQueue, 180);
      return;
    }
  }
  var job=announceQueue.shift();
  /* Pasenęs soft darbas (nudge/joke/phone/guitar laukė >25 s) — išmetam, kad Vilkas nekalbėtų apie praeitį. */
  if(job && job.queuedAt && (job.tag==='nudge'||job.tag==='joke'||job.tag==='phone'||job.tag==='guitar'||job.tag==='sing') && Date.now()-job.queuedAt>25000){
    if(job.onDone && job.tag==='phone') try{ job.onDone(); }catch(e){}
    setTimeout(runAnnounceQueue, 0);
    return;
  }
  announceBusy=true;
  announceCurrentJob=job;
  var jobEpoch=announceEpoch;
  if(announceQueue[0]) prefetchTts(announceQueue[0].text, announceQueue[0].fast, announceQueue[0].speed);
  /* 1) Pirma užkraunam balsą — Vilkas dar NĖRA scenoje */
  var prep = (job.playMs || !job.text) ? Promise.resolve(null) : loadTtsUrl(job.text, !!job.fast, job.speed).catch(function(){ return null; });
  prep.then(function(audioUrl){
    if(jobEpoch!==announceEpoch) return;
    if(job.applause){ try{ bidApplauseSound(); }catch(e){} }
    function doSpeak(){
      var popEl=document.getElementById('wolfPop');
      if(popEl){ popEl.classList.remove('coffee','side'); if(job.cls) popEl.classList.add(job.cls); }
      if(job.bangsBefore) setPose(job.pose||'raise');
      else setPose(job.pose||'raise');
      if(job.onSpeak) try{ job.onSpeak(); }catch(e){}
      if(job.fx==='heart') heartBurst(); else if(job.fx==='cheer') cheerBurst(); else if(job.fx==='splash') splashBurst(); else if(job.fx==='notes') notesBurst(); else if(job.fx==='laugh'){ laughBurst(); try{ wolfLaughSound(); }catch(e){} } else if(job.fx==='rock') rockBurst();
      var say = job.playMs ? function(t, cb, onStart){
        setBubble(job.bubble||null, ''); var b=document.getElementById('wolfPopBubble'); if(b) b.classList.add('open'); wolfPopTalking(true); setMusicDuck(true); onStart();
        setTimeout(function(){ wolfPopTalking(false); setMusicDuck(false); if(b) b.classList.remove('open'); cb(); }, job.playMs);
      } : function(t, cb, onStart){
        speakHost(t, cb, onStart, {bubble: job.bubble, fast: job.fast, speed: job.speed, audioUrl: audioUrl, gen: speakGen});
      };
      say(job.text, function(){
        if(jobEpoch!==announceEpoch) return;
        stopGestures();
        if(popEl && !job.keepCls) popEl.classList.remove('coffee','side');
        bangHammer(job.bangs==null?1:job.bangs, function(){
          if(jobEpoch!==announceEpoch) return;
          if(job.after) setPose(job.after);
          announceBusy=false;
          announceCurrentJob=null;
          if(job.onDone) try{ job.onDone(); }catch(e){}
          if(announceQueue.length) setTimeout(runAnnounceQueue, 180);
          else if(job.stay && coffeeActive){ setPose('coffee'); var pe=document.getElementById('wolfPop'); if(pe) pe.classList.add('coffee'); setBubble('', ''); }
          else wolfPopHideSoon(job.after?500:280);
        });
      }, function(){ startGestures(job.gestures, job.gestureMs); });
    }
    function appearThenSpeak(){
      clearSmoke();
      wolfPopShow(job.pose||'raise');
      /* Pop animacija ~0.28s — tada balsas+lentelė+judesiai kartu */
      setTimeout(doSpeak, job.bangsBefore ? 80 : 280);
    }
    if(job.bangsBefore){
      clearSmoke();
      wolfPopShow('raise');
      bangHammer(job.bangsBefore, appearThenSpeak, job.gong);
    } else {
      appearThenSpeak();
    }
  });
}
var visualAnnTimer=null;
function runVisualAnnounce(text, opts){
  /* Telefonas / antras tabas: BE TTS (balsas tik audio-master), bet Vilkas MATOMAS + kalbos poza. */
  if(typeof isVilkasStageOn==='function' && !isVilkasStageOn()) return;
  if(phoneAway) return;
  opts=opts||{};
  try{ wolfPopShow(opts.pose||'present'); }catch(e){}
  try{ clearTimeout(visualAnnTimer); }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){ pop.classList.remove('hide','coffee','side'); if(opts.cls) pop.classList.add(opts.cls); }
  }catch(e){}
  try{ setPose(opts.pose||'raise'); }catch(e){}
  try{ wolfPopTalking(true); }catch(e){}
  try{ if(opts.gestures) startGestures(opts.gestures, opts.gestureMs); }catch(e){}
  try{
    if(opts.fx==='cheer') cheerBurst();
    else if(opts.fx==='heart') heartBurst();
    else if(opts.fx==='laugh') laughBurst();
    else if(opts.fx==='splash') splashBurst();
    else if(opts.fx==='notes') notesBurst();
    else if(opts.fx==='rock') rockBurst();
  }catch(e){}
  try{ if(opts.onSpeak) opts.onSpeak(); }catch(e){}
  var ms=opts.playMs||Math.min(10000, Math.max(1800, String(text||opts.text||'').length*50));
  visualAnnTimer=setTimeout(function(){
    visualAnnTimer=null;
    try{ wolfPopTalking(false); }catch(e){}
    try{ stopGestures(); }catch(e){}
    try{ if(opts.after) setPose(opts.after); }catch(e){}
    try{ if(opts.onDone) opts.onDone(); }catch(e){}
    try{ wolfPopShow(opts.after||opts.pose||'raise'); }catch(e){}
  }, ms);
}
function queueAnnounce(text, opts){
  if(typeof isVilkasStageOn==='function' && !isVilkasStageOn()) return; /* izanga — Vilkas tyli */
  if(typeof opts!=='object' || opts===null) opts={applause:!!opts};
  opts.text=text;
  try{ wolfPopShow((opts && opts.pose) || 'present'); }catch(e){}
  /* Balsas tik audio-master; VAIZDAS — visiems (telefonas be TTS, su kalbos poza). */
  if(!isCoverMode() && typeof isAudioMaster==='function' && !isAudioMaster()){
    runVisualAnnounce(text, opts);
    return;
  }
  if(!pageAllowsAudio()) return; /* tab hidden */
  opts.queuedAt=Date.now();
  var key=announceJobKey(opts);
  if(key && key!=='|'){
    for(var i=0;i<announceQueue.length;i++){
      if(announceJobKey(announceQueue[i])===key) return;
    }
    if(announceBusy && announceCurrentJob && announceJobKey(announceCurrentJob)===key) return;
  }
  if(opts.priority) announceQueue.unshift(opts);
  else announceQueue.push(opts);
  prefetchTts(text, opts.fast);
  runAnnounceQueue();
}
function maybeAnnounceBid(state){
  // DISABLED: server director owns this
  return;
  if(!state || !state.bids || !state.bids.length) return;
  var b=state.bids[0];
  var key=String(b.at)+'|'+b.name+'|'+b.amount;
  if(lastBidKey===null){ lastBidKey=key; return; } // nepranešti istorinių
  if(key===lastBidKey) return;
  /* Tavo paspaudimas jau paskelbtas iš serverio atsakymo — nekartoti. */
  if(locallyAnnouncedBid &&
     locallyAnnouncedBid.name===b.name &&
     Number(locallyAnnouncedBid.amount)===Number(b.amount)){
    locallyAnnouncedBid=null;
    lastBidKey=key;
    return;
  }
  lastBidKey=key;
  var isFirst = state.bids.length===1;
  silence.bidAt=Date.now(); silence.stage=0;
  /* interruptAllSpeech viduje speakBidNow — senas balsas miršta */
  if(coffeeActive) endCoffee();
  speakBidNow(b.name, b.amount);
  scheduleTradePhoneCall();
}

var silence={lotId:null, bidAt:0, stage:0, nudged:{}};
function cuteName(name){
  var w=String(name||'').trim().split(/\s+/)[0];
  if(!w) return 'gražuole';
  if(/^oksana$/i.test(w)) return 'Oksanka';
  if(/^vanessa$/i.test(w)) return 'Vanessa';
  if(/ita$/i.test(w)) return w.replace(/ita$/i,'yte'); /* Brigita → Brigyte */
  if(/ė$/i.test(w)) return w.replace(/ė$/i,'yte');     /* Giedrė → Giedryte */
  if(/a$/i.test(w)) return w.replace(/a$/i,'ute');     /* Laura → Laurute */
  return vocative(w);
}
/* Naujos damos — kai dvi prisijungia: „Ooo! Dar dvi damos… Paplokime!“ */
var seenJoinNames = {};
var seenJoinEventIds = null;
var pendingDames = [];
var dameBatchTimer = null;
function announceTwoDames(a, b){
  var line='Ooooo! '+a+'! Paplokite — prisijungė! Ooo ir '+cuteName(b)+'!';
  queueAnnounce(line, {
    pose:'clap', bangs:0, applause:true,
    gestures:CLAP.concat(['wink','glasses','wink']), gestureMs:360,
    bubble:'👏 Oooo! '+a+' ir '+b+'!',
    fx:'cheer'
  });
}
function noteNewDame(name){
  var w=String(name||'').trim().split(/\s+/)[0];
  if(!w || !isFemaleName(w)) return false;
  if(seenJoinNames[w]) return false;
  seenJoinNames[w]=true;
  if(pendingDames.indexOf(w)>=0) return false;
  pendingDames.push(w);
  if(pendingDames.length>=2){
    clearTimeout(dameBatchTimer); dameBatchTimer=null;
    var x=pendingDames.shift(), y=pendingDames.shift();
    announceTwoDames(x, y);
    return true;
  }
  clearTimeout(dameBatchTimer);
  dameBatchTimer=setTimeout(function(){
    dameBatchTimer=null;
    if(pendingDames.length===1){
      var one=pendingDames.shift();
      queueAnnounce('Ooo! Dama '+cuteName(one)+' su mumis! Sveikinam — paplokime!', {
        pose:'wink', bangs:0, applause:true,
        gestures:['wink','clap','wink'], bubble:'👏 '+one
      });
    }
  }, 45000);
  return true;
}
function maybeAnnounceNewJoins(st){
  // Prisijungimas keičia tik dalyvių sąrašą; balsinio sveikinimo nėra.
  clearTimeout(dameBatchTimer);
  pendingDames=[];
  return;
}
/* Trumpas profesionalus raginimas vardu — be atsitiktinių asmeninių prielaidų. */
function encourageBidLine(name){
  var n=String(name||'').trim().split(/\s+/)[0]||'drauge';
  var v=vocative(n);
  if(isFemaleName(n)){
    return pick([
      n+', tavo ėjimas — jei patinka, spausk KELTI!',
      v+', dar vienas euras ir tu priekyje!',
      n+', Vilkas mato gerą skonį — judam!',
      'Na ką, '+v+' — ar imam šitą lotą?'
    ]);
  }
  return pick([
    v+', tavo ėjimas — spausk KELTI!',
    n+', dar vienas euras ir tu priekyje!',
    n+', Vilkas laukia tavo ėjimo!',
    'Na ką, '+v+' — ar imam šitą lotą?'
  ]);
}
function pickEncourageTarget(){
  var names=(state && state.participant_names)||[];
  var lead=state && state.lot && state.lot.current_bidder;
  var lead0=lead ? String(lead).split(' ')[0] : '';
  var pool=names.filter(function(n){
    var w=String(n||'').split(' ')[0];
    return w && w!==lead0 && w!=='Mindaugas';
  });
  if(!pool.length) pool=names.filter(Boolean);
  return pool.length ? pick(pool) : null;
}
function otherParticipant(){
  return pickEncourageTarget();
}
var START_LINE='Pradedame! Minutė prasideda — spauskite KELTI mygtuką! Kas pirmas?';
var presented={}, armedLot=null, startFlashUntil=0, lastGreenN=null;
function splitList(s){ return String(s||'').split(/[;\n]+/).map(function(x){return x.trim();}).filter(Boolean); }
var CONDITION_WORDS={nauja:'visiškai nauja', kaip_nauja:'kaip nauja', gera:'geros būklės', naudota:'naudota, bet dar tarnaus'};
function showShowcase(lot){
  return; /* vidurinė prekės kortelė išjungta – viską apibūdina Vilkas */
  var sc=document.getElementById('showcase'); if(!sc) return;
  var img=document.getElementById('showcaseImg');
  if(lot.photo_file){ img.src='/photos/'+lot.photo_file; img.style.display='block'; } else img.style.display='none';
  document.getElementById('showcaseTitle').textContent=lot.title||'';
  var h='', d=0;
  function chip(cls, t){ h+='<span class="chip '+cls+'" style="animation-delay:'+(0.5+d*0.35)+'s">'+esc(t)+'</span>'; d++; }
  splitList(lot.pluses).forEach(function(p){ chip('plus','✅ '+p); });
  splitList(lot.defects).forEach(function(p){ chip('def','⚠️ '+p); });
  splitList(lot.included).forEach(function(p){ chip('inc','📦 '+p); });
  chip('price','Pradinė kaina '+fmt(lot.starting_price||lot.current_price)+' €');
  document.getElementById('showcaseChips').innerHTML=h;
  sc.classList.remove('hide'); restartClass(sc,'show');
}
function hideShowcase(){
  var sc=document.getElementById('showcase'); if(!sc || !sc.classList.contains('show')) return;
  sc.classList.remove('show'); restartClass(sc,'hide');
}
function presentLot(lot){
  presented[lot.id]=true;
  var pl=splitList(lot.pluses), df=splitList(lot.defects), inc=splitList(lot.included);
  var cond=CONDITION_WORDS[String(lot.condition||'').toLowerCase()]||'';
  var intro=pick(['O dabar — dėmesio!','Ponai ir ponios, žiūrėkit, ką turiu!','Tūkstantis perkūnų, koks lotas!','Paruoškit pinigines — ir širdis!'])+
    ' Lotas numeris '+lot.lot_number+' — '+lot.title+'!'+(cond?' Būklė — '+cond+'.':'');
  /* Retas asmeninis prisiminimas — ne prie kiekvieno loto. */
  if(Math.random()<0.28 && /(samsung|galaxy|iphone|nokia|motorola|alcatel|phone)/i.test(String(lot.title||''))){
    intro+=pick([
      ' Ooo, aš tokį turėjau prieš trejus metus!',
      'Ooo, toks telefonas man buvo rankose prieš trejus metus!',
      'Prisiminiau — prieš trejus metus su tokiu telefonu vaikščiojau!'
    ]);
  }
  var details='';
  if(pl.length) details+=' Pliusai: '+pl.slice(0,4).join(', ')+'.';
  if(df.length) details+=' Defektai, sąžiningai: '+df.slice(0,3).join(', ')+'. '+pick([
    'Viskas pasakyta atvirai — sprendimas jūsų.',
    'Maži niuansai, bet kaina tai žino.',
    'Nieko neslepiam — žinot, ką perkat.',
    'Būklė įvertinta sąžiningai, o daiktas dar turi parako.',
    'Svarbiausia — veikia ir laukia naujo šeimininko.'
  ]);
  else details+=' Defektų — nerasta, tikrinau su lupa!';
  if(inc.length) details+=' Pridedu: '+inc.slice(0,3).join(', ')+'.';
  var price=lot.starting_price||lot.current_price;
  var t1=intro+details, t2='Pradinė kaina — '+eurosWords(price)+'! Spauskite KELTI mygtuką — ruoškitės!';
  var brainPayload={
    lot_number:lot.lot_number, title:lot.title, description:lot.description||'',
    condition:cond, pluses:pl.join('; '), defects:df.join('; '), included:inc.join('; '),
    price:price, starting_price:price
  };
  if(coffeeActive) endCoffee();
  var waited=0;
  (function go(){
    if((announceBusy || announceQueue.length) && waited<50000){ waited+=300; return setTimeout(go, 300); }
    if(lot.starts_at*1000-Date.now() < 12000){ armedLot=lot.id; return; }
    Promise.all([Promise.resolve(t1), Promise.resolve(t2)]).then(function(lines){
      prefetchTts(lines[0]); prefetchTts(lines[1]); prefetchTts(START_LINE);
      runPresentation(lot, lines[0], lines[1], price);
    });
  })();
}
function runPresentation(lot, t1, t2, price){
  fanfareIntro();
  wolfPopShow('clap','🥁 Dėmesio! Naujas lotas!');
  setTimeout(function(){ welcomeWolfForLot(lot); }, 1000);
  startGestures(CLAP, 330);
  setTimeout(function(){
    stopGestures();
    queueAnnounce(t1, {tag:'present', pose:'present', cls:'side', keepCls:true, bangs:0, gestures:['present','welcome','present','thumb'],
      bubble:'🎤 Lotas #'+lot.lot_number+': '+lot.title});
    queueAnnounce(t2, {tag:'present', pose:'raise', cls:'side', bangs:1, fx:'cheer', gestures:['raise','welcome','raise'],
       bubble:'💰 Pradinė kaina '+fmt(price)+' €!', onSpeak:function(){ armedLot=lot.id; setTimeout(hideShowcase, 3500); }});
  }, 3300);
}
function maybePresent(lot){
  if(!lot || lot.status!=='live' || !lot.starts_at || presented[lot.id]) return;
  var r=lot.starts_at*1000-Date.now();
  if(r>16000) presentLot(lot);
  else { presented[lot.id]=true; armedLot=lot.id; }
}
function setBtn(cls, label, time){
  var b=els.bidBtn;
  ['armed','go-green','start-pop','hurry'].forEach(function(c){ if(c!==cls && !(cls==='hurry' && c==='hurry')) b.classList.remove(c); });
  if(cls && !b.classList.contains(cls)) b.classList.add(cls);
  if(label!=null){ els.bidLabel.textContent=label; }
}
function tickButton(){
  var lot=state && state.lot;
  if(!els.bidBtn) return;
  if(!lot || lot.status==='ended'){
    els.bidBtn.classList.remove('armed','go-green','start-pop','hurry');
    return;
  }
  if(state && state.auction_locked){
    return;
  }
  var now=Date.now();
  if(lot.starts_at && lot.starts_at*1000>now){
    var r=(lot.starts_at*1000-now)/1000;
    els.bidBtn.disabled=true;
    if(r>9.5){
      lastGreenN=null;
      if(armedLot===lot.id) setBtn('armed','KELTI KAINĄ +1 €');
      else setBtn(null,'🎤 Vilkas pristato…');
    } else {
      var n=Math.max(1,Math.ceil(r));
      if(lastGreenN===null){ armedLot=lot.id; hideShowcase(); }
      if(n!==lastGreenN){ lastGreenN=n; tickSound(); restartClass(els.bidBtn,'go-green'); }
      setBtn('go-green', String(n));
    }
    return;
  }
  if(lastGreenN!==null){
    lastGreenN=null; startFlashUntil=now+1300; startSound();
    announceQueue=announceQueue.filter(function(j){ return j.tag!=='present'; });
    hideShowcase();
  }
  if(now<startFlashUntil){
    setBtn('start-pop','🚀 START!');
    els.bidBtn.disabled=true;
    return;
  }
  var left=lot.ends_at ? Math.max(0, lot.ends_at*1000-now) : 60000;
  els.bidBtn.classList.remove('armed','go-green','start-pop');
  els.bidBtn.classList.toggle('hurry', left<10000);
  if(state && state.auction_locked){ els.bidBtn.disabled=true; return; }
  if(!myPid){
    els.bidBtn.disabled=true;
    els.bidLabel.textContent='Užsiregistruok';
    return;
  }
  if(lot.current_bidder===myNickname){
    els.bidBtn.disabled=true;
    els.bidLabel.textContent='👑 TU LYDERIAUJI';
  } else {
    els.bidBtn.disabled=false;
    els.bidLabel.textContent='KELTI KAINĄ +1 €';
  }
}
function watchSilence(){
  // DISABLED: server director owns this (nudge/phone/joke)
  return;
  var lot=state && state.lot;
  if(!lot || lot.status==='ended' || !lot.ends_at || (lot.starts_at && lot.starts_at*1000>Date.now())) return;
  if(silence.lotId!==lot.id){ silence={lotId:lot.id, bidAt:Date.now(), stage:0, finale:false}; return; }
  if(announceBusy || announceQueue.length || coffeeActive) return;
  var quiet=(Date.now()-silence.bidAt)/1000;
  var remain=(lot.ends_at*1000-Date.now())/1000;
  /* Paskutinės sekundės: nestabdom + vardas */
  if(!silence.finale && remain<=9 && remain>2){
    silence.finale=true;
    var who=pickEncourageTarget();
    var line='Nu kas pakels dar? Nu — nestabdom, nestabdo, judam!';
    if(who) line+=' '+encourageBidLine(who);
    var pose=who && isFemaleName(who) ? 'wink' : 'raise';
    queueAnnounce(line, {pose:pose, bangs:0, gestures:[pose,'welcome','raise'], bubble:'⏰ Nu kas pakels dar?'});
    return;
  }
  /* Viduryje tylos — vienas raginimas vardu (be bajeriukų / kavutės) */
  if(silence.stage===0 && quiet>12 && remain>18){
    silence.stage=1;
    var who2=pickEncourageTarget();
    if(who2){
      var pose2=isFemaleName(who2)?'wink':'thumb';
      queueAnnounce(encourageBidLine(who2), {
        pose:pose2, bangs:0,
        gestures:isFemaleName(who2)?['wink','glasses','wink']:['thumb','raise','thumb'],
        bubble:'👉 '+String(who2).split(' ')[0]
      });
    } else {
      wolfPopHideSoon(80);
    }
    return;
  }
  /* Ilgai niekas neperka — žemaitiškai arba skambutis */
  if(silence.stage===1 && quiet>26 && remain>14){
    silence.stage=2;
    if(Math.random()<0.45){
      playPhoneCallGag();
    } else {
      /* Ilgas lėtas LT tarimas — BE žodžio „tyla“ */
      var zem=pick([
        'Nu kas čia — keliam?',
        'Nu… kas čia? Keliam?',
        'Kas čia — keliam aukščiau?',
        'Nu kas čia — kas kels?',
        'Nu kas čia? Spauskit mygtuką — keliam!'
      ]);
      queueAnnounce(zem, {pose:'raise', bangs:0, gestures:['raise','welcome','raise'], bubble:'❓ Nu kas čia — keliam?', speed:0.7, fast:false});
    }
    return;
  }
  /* Dar tyla — kitas efektas (jei anksčiau nebuvo skambučio) */
  if(silence.stage===2 && quiet>38 && remain>12){
    silence.stage=3;
    if(Math.random()<0.55) playPhoneCallGag();
    else wolfPopHideSoon(80);
    return;
  }
  if(silence.stage===3 && quiet>50){
    silence.stage=4;
    wolfPopHideSoon(80);
  }
}
function doSilenceAct(lot, remain, key){
  wolfPopHideSoon(80);
}
function speakSold(name, price, lotId){
  var n=String(name||'').split(' ')[0]||'drauge';
  var line='Parduota! Plojimai!';
  queueAnnounce(line, {tag:'sold', pose:isFemaleName(name)?'wink':'welcome', bangsBefore:3, gong:true, bangs:0, after:'bow',
    fx:isFemaleName(name)?'heart':'cheer', gestures:CLAP.concat(isFemaleName(name)?['wink','glasses','wink']:['thumb','welcome']), gestureMs:380,
    bubble:'🏆 PARDUOTA! '+(isFemaleName(name)?'Gražuolė ':'Šaunuolis ')+n+'!',
    onSpeak:function(){ try{ celebrationSound(); }catch(e){} try{ photographedWolf('🏆 Parduota!', currentPose); }catch(e){} },
    onDone:function(){
      /* Kava TIK kai nėra kito loto — kitaip Vilkas turi IŠKART pristatyti lot_intro */
      try{
        for(var i=0;i<announceQueue.length;i++){
          if(announceQueue[i] && announceQueue[i].tag==='lot_intro') return;
        }
        if(announceBusy && announceCurrentJob && announceCurrentJob.tag==='lot_intro') return;
      }catch(e){}
      /* Be kito loto kavą paleidžia intermission handler (ne čia dubliuoti) */
    }});
}
function speakLotStart(){
  // DISABLED: server director owns this
  return;
  if(coffeeActive) endCoffee();
  queueAnnounce(START_LINE, {tag:'start', pose:'welcome', bangsBefore:1, gong:true, bangs:0, gestures:CLAP.concat(['raise']), bubble:'🔨 PRADEDAME! Kas pirmas?'});
}

var radioStarting = false;
/* Po Vilko kalbos radijas garsiau; kalbant — duck žemyn */
var MUSIC_DUCK_RATIO = 0.80;
var MUSIC_TARGET_VOL = 0.82;
var MUSIC_DUCK_VOL = MUSIC_TARGET_VOL*MUSIC_DUCK_RATIO;
var DESK_SONG_VOL = 0.86;
var radioTargetVol = MUSIC_TARGET_VOL;
var radioDuckVol = MUSIC_DUCK_VOL;
function syncPracticeMusicLevels(){
  /* Kalbant muzika sumažinama 20% nuo atitinkamo įprasto lygio. */
  radioTargetVol=practiceModeOn?0.88:0.82;
  radioDuckVol=radioTargetVol*MUSIC_DUCK_RATIO;
}
var radioFadeTimer = null;
var WOLF_VOICE_VOL = 0.81;
var WOLF_VOICE_BOOST = 1.75;
var WOLF_ECHO_DELAY_S = 0.26;
var WOLF_ECHO_GAIN = 0.18;
var wolfVoiceAudioContext = null;
var RADIO_STATIONS = [
  /* /radio/club = same-origin proxy — jokių geo/CORS blokų; fallback = tiesioginis upstream */
  {id:'club', name:'Bendruomenės klubas', url:'/radio/club', fallback:'https://streams.ilovemusic.de/iloveradio14.mp3', segment:'ilovepartyhard', fallbackSegment:'ilovepartyhard'},
  {id:'dance', name:'Šokiai', url:'https://stream.powerhitradio.lt/PHR_AAC', fallback:'https://stream.m-1.fm/m1/mp3', segment:'', fallbackSegment:''},
  {id:'m1', name:'M-1', url:'https://stream.m-1.fm/m1/mp3', fallback:'', segment:'', fallbackSegment:''}
];
var radioStationId = 'club';
var radioLabel = 'Bendruomenės klubas';
var radioUrlTry = 0;
var energyWatchTimer = null;
var slowEnergyStreak = 0;
var SLOW_ENERGY_SECONDS = 22;
var radioPeakHistory = [];

function getRadioEl(){
  return document.getElementById('vilkasRadioPlayer');
}
function getRadioStation(id){
  id=id||radioStationId;
  for(var i=0;i<RADIO_STATIONS.length;i++){
    if(RADIO_STATIONS[i].id===id) return RADIO_STATIONS[i];
  }
  return RADIO_STATIONS[0];
}
function radioStreamUrl(){
  var st=getRadioStation(radioStationId);
  return (radioUrlTry===1 && st.fallback) ? st.fallback : st.url;
}
function radioSrcMatches(el, url){
  if(!el || !url) return false;
  var cur=(el.currentSrc||el.src||'').split('?')[0];
  var want=String(url).split('?')[0];
  if(!cur || !want) return false;
  if(cur===want || cur.indexOf(want)>=0 || want.indexOf(cur)>=0) return true;
  /* relative /radio/club vs absolute https://host/radio/club */
  try{
    if(want.charAt(0)==='/' && cur.indexOf(want)>=0) return true;
    if(want.indexOf('/radio/club')>=0 && cur.indexOf('/radio/club')>=0) return true;
  }catch(e){}
  return false;
}
/* Srautas gyvas (gali būti muted — Chrome autoplay) */
function radioHasLiveStream(){
  var el=getRadioEl();
  if(!el) return false;
  var src=el.currentSrc||el.src||'';
  return !!src && !el.paused && !el.ended;
}
/* Žmogus GIRDI */
function radioIsPlaying(){
  var el=getRadioEl();
  if(!el) return false;
  return radioHasLiveStream() && !el.muted && Number(el.volume||0)>0.01;
}
/* Unmute + volume — NENAIKINTI src (teardown = tyla iki bufferio) */
function makeRadioAudibleNow(){
  if(stageMusicMuted()){ muteMusicForStage(); return false; }
  if(deskSongOn) return false;
  var el=getRadioEl();
  if(!el || !musicOn) return false;
  if(document.visibilityState==='hidden') return false;
  if(isCoverMode()){ try{ claimAudioMaster(true); }catch(e){} }
  else if(vilkasStageOn){ if(!isAudioMaster()) return false; }
  else { try{ claimAudioMaster(true); }catch(e){} }
  try{
    el.muted=false;
    el.defaultMuted=false;
    el.removeAttribute('muted');
    el.volume=radioVolumeForCurrentState();
  }catch(e){}
  if(!radioHasLiveStream()){
    try{ startMusic(true); }catch(e){}
    return radioIsPlaying();
  }
  try{
    var p=el.play();
    if(p && p.catch) p.catch(function(){});
  }catch(e){}
  return radioIsPlaying();
}
function forceRadioAudible(){ return makeRadioAudibleNow(); }
/* Palaikyti srautą: jei jau groja (net muted) — NELIESTI src */
function keepRadioAlive(){
  if(stageMusicMuted()){ muteMusicForStage(); return; }
  if(deskSongOn){
    try{ softPauseRadioKeepSrc(); }catch(e){}
    var rr=getRadioEl();
    if(rr){ try{ rr.muted=true; rr.volume=0; }catch(e2){} }
    var s=getDeskSongEl();
    if(s && (s.paused || s.ended)){
      try{ var ps=s.play(); if(ps&&ps.catch) ps.catch(function(){}); }catch(e3){}
    }
    return;
  }
  var el=getRadioEl();
  if(!el || !musicOn) return;
  if(document.visibilityState==='hidden') return;
  if(isCoverMode()){ try{ claimAudioMaster(true); }catch(e){} }
  else if(vilkasStageOn){
    if(!isAudioMaster()) return;
    try{ localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()})); }catch(e){}
  } else { try{ claimAudioMaster(true); }catch(e){} }
  var url=radioStreamUrl();
  if(radioHasLiveStream() && radioSrcMatches(el, url)){
    /* jau bufferina/groja — bandyti unmute (be gesto Chrome gali atmesti — OK) */
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=radioVolumeForCurrentState();
    }catch(e){}
    try{ var p=el.play(); if(p&&p.catch) p.catch(function(){}); }catch(e){}
    return;
  }
  if(!radioStarting) try{ startMusic(true); }catch(e){}
}
function pauseRadio(){
  hardKillRadio();
}
function resumeRadio(steal){
  if(!musicOn) return;
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  if(!isAudioMaster() && !claimAudioMaster(steal)) return;
  if(!isAudioMaster()) return;
  if(radioIsPlaying() || radioStarting) return;
  startMusic(steal);
}
function stopEnergyWatch(){
  if(energyWatchTimer){ clearInterval(energyWatchTimer); energyWatchTimer=null; }
  slowEnergyStreak=0;
  radioPeakHistory=[];
}
/* Diskotekos fonas įžangoje — zibintai pagal muzikos taktą */
var discoRaf=null, discoPrevBass=0, discoHue=0, discoLastBeat=0;
/* Vienas captureStream visam — ne dubliuoti garsą */
var radioAnalyserCtx=null, radioAnalyserSrc=null, radioAnalyserNode=null;
function releaseRadioAnalyser(){
  try{ if(radioAnalyserSrc) radioAnalyserSrc.disconnect(); }catch(e){}
  radioAnalyserSrc=null; radioAnalyserNode=null;
  try{ if(radioAnalyserCtx && radioAnalyserCtx.state!=='closed') radioAnalyserCtx.close(); }catch(e){}
  radioAnalyserCtx=null;
}
function getRadioAnalyser(){
  /* Įžangoje captureStream + šokėjų mp4 = Chrome stabdo vaizdą. Tik fake beat. */
  try{
    if(document.body.classList.contains('cover-mode') && document.querySelector('.dd-video')){
      return null;
    }
  }catch(e){}
  if(!radioIsPlaying()) return null;
  if(radioAnalyserNode) return radioAnalyserNode;
  var el=getRadioEl();
  if(!el || typeof el.captureStream!=='function') return null;
  try{
    radioAnalyserCtx=new (window.AudioContext||window.webkitAudioContext)();
    radioAnalyserSrc=radioAnalyserCtx.createMediaStreamSource(el.captureStream());
    radioAnalyserNode=radioAnalyserCtx.createAnalyser();
    radioAnalyserNode.fftSize=2048;
    radioAnalyserNode.smoothingTimeConstant=0.72;
    radioAnalyserSrc.connect(radioAnalyserNode);
    if(radioAnalyserCtx.state==='suspended') radioAnalyserCtx.resume();
  }catch(e){ releaseRadioAnalyser(); return null; }
  return radioAnalyserNode;
}
function keepDancerVideoAlive(){
  if(!document.body.classList.contains('cover-mode')) return;
  if(document.visibilityState==='hidden') return;
  try{
    document.querySelectorAll('.dd-video').forEach(function(v){
      try{
        v.muted=true; v.defaultMuted=true; v.loop=true; v.playsInline=true;
        v.setAttribute('playsinline',''); v.setAttribute('muted','');
        var spin=v.closest?v.closest('.dd-spin'):null;
        if(spin && v.dataset.swapBusy!=='1' && spin.style.opacity==='0') spin.style.opacity='1';
        if(v.paused || v.ended){
          var p=v.play();
          if(p&&p.catch) p.catch(function(){});
        }
      }catch(e){}
    });
  }catch(e){}
}
setInterval(keepDancerVideoAlive, 700);
var discoDancers=[], discoBeatBoost=0;
function lerp(a,b,t){ return a+(b-a)*t; }
function initDiscoDancers(){
  if(discoDancers.length) return;
  document.querySelectorAll('.disco-dancer').forEach(function(el,i){
    discoDancers.push({
      spin:el.querySelector('.dd-spin'),
      idx:i,
      seed:i*1.37+0.4,
      sway:0, bob:0, lean:0, skew:0, stretch:1,
      tSway:0, tBob:0, tLean:0, tSkew:0, tStretch:1
    });
  });
}
function updateDiscoDancers(strength,onBeat){
  initDiscoDancers();
  if(!discoDancers.length) return;
  var t=performance.now()/1000;
  var s=Math.max(0.35, Math.min(1.2, strength||0.45));
  if(onBeat) discoBeatBoost=1;
  discoBeatBoost*=0.90;
  var pulse=discoBeatBoost;
  discoDancers.forEach(function(d){
    var p=d.seed;
    /* VOS VOS — rėmelis beveik stovi (Mindaugas: anksčiau nesisiūbavo stipriai). */
    d.tSway = Math.sin(t*(1.4+p*0.15)+p)*1.6*s;
    d.tBob = 0.4 + (0.5+0.5*Math.sin(t*(3.2+p*0.2)+p*2.0))*1.4*s + pulse*1.2;
    d.tLean = Math.sin(t*(1.2+p*0.12)+p*0.8)*0.22*s;
    d.tSkew = 0;
    d.tStretch = 1 + pulse*0.006;
    var ease=0.06;
    d.sway=lerp(d.sway,d.tSway,ease);
    d.bob=lerp(d.bob,d.tBob,ease);
    d.lean=lerp(d.lean,d.tLean,ease);
    d.stretch=lerp(d.stretch,d.tStretch,ease);
    if(d.spin) d.spin.style.transform='translate('+d.sway.toFixed(1)+'px,'+(-d.bob).toFixed(1)+'px) rotate('+d.lean.toFixed(2)+'deg) scale('+d.stretch.toFixed(3)+')';
  });
  try{
    document.querySelectorAll('.dd-video').forEach(function(v){
      if(v.paused){ var pr=v.play(); if(pr&&pr.catch) pr.catch(function(){}); }
    });
  }catch(e){}
}
function resetDiscoDancers(){
  discoDancers=[]; discoBeatBoost=0;
}
function setDiscoVisible(on){
  var f=document.getElementById('discoField');
  if(!f) return;
  var show=!!on && document.body.classList.contains('cover-mode') && document.visibilityState!=='hidden';
  f.classList.toggle('on', show);
  f.setAttribute('aria-hidden', show?'false':'true');
  if(!show) f.classList.remove('beat');
}
function stopDiscoBeat(){
  if(discoRaf){ try{ cancelAnimationFrame(discoRaf); }catch(e){} discoRaf=null; }
  try{ if(typeof dancerTimer!=='undefined'&&dancerTimer){ clearTimeout(dancerTimer); dancerTimer=null; } }catch(e){}
  setDiscoVisible(false);
  discoPrevBass=0;
  resetDiscoDancers();
}
function startDiscoBeat(){
  if(discoRaf) return; /* jau veikia — neperkrauti */
  if(!document.body.classList.contains('cover-mode')) return;
  setDiscoVisible(true);
  var spots=document.querySelectorAll('#discoField .disco-spot');
  var beams=document.querySelectorAll('#discoField .disco-beam');
  var field=document.getElementById('discoField');
  var fakePhase=0;
  function pulseBeat(strength){
    var now=performance.now();
    if(now-discoLastBeat<140) return;
    discoLastBeat=now;
    if(!field) return;
    field.classList.remove('beat');
    void field.offsetWidth;
    field.classList.add('beat');
    discoHue=(discoHue+37+(strength*40))%360;
    /* klubo spalva — seka video foną (auto hue), default mėlyna */
    var DH=(typeof window.__DH==='number')?window.__DH:212;
    var cols=[
      'hsla('+DH+',100%,60%,.68)',
      'hsla('+((DH+340)%360)+',100%,55%,.62)',
      'hsla('+((DH+20)%360)+',100%,64%,.62)',
      'hsla('+((DH+350)%360)+',100%,72%,.55)',
      'hsla('+((DH+40)%360)+',100%,66%,.58)'
    ];
    for(var i=0;i<spots.length;i++) spots[i].style.background=cols[i%cols.length];
    for(var b=0;b<beams.length;b++){
      beams[b].style.opacity=String(0.2+strength*0.55);
      beams[b].style.transform='rotate('+((-18+b*14)+strength*8)+'deg)';
    }
    try{ updateDiscoDancers(strength,true); }catch(e){}
  }
  function tick(){
    discoRaf=requestAnimationFrame(tick);
    if(!document.body.classList.contains('cover-mode') || document.visibilityState==='hidden'){
      setDiscoVisible(false);
      return;
    }
    setDiscoVisible(true);
    var bass=0, strength=0.35, radioLive=radioIsPlaying();
    var analyser=radioLive ? getRadioAnalyser() : null;
    if(analyser && radioLive){
      try{
        if(radioAnalyserCtx && radioAnalyserCtx.state==='suspended') radioAnalyserCtx.resume();
        var freq=new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(freq);
        var n=Math.min(24, freq.length), sum=0;
        for(var i=0;i<n;i++) sum+=freq[i];
        bass=sum/(n*255);
        strength=Math.min(1, bass*1.8);
        if(bass>0.12 && bass>discoPrevBass*1.12) pulseBeat(strength);
        discoPrevBass=bass*0.82+discoPrevBass*0.18;
      }catch(e){}
    } else {
      /* fallback — ~120 BPM pulsas jei analyser neprieinamas */
      fakePhase+=1;
      if(fakePhase%28===0) pulseBeat(0.55);
    }
    /* švelnus nuolatinis judesys */
    for(var s=0;s<spots.length;s++){
      var o=0.35+strength*0.45+(Math.sin(performance.now()/400+s)*0.08);
      spots[s].style.opacity=String(Math.max(0.2, Math.min(0.85, o)));
    }
    try{ updateDiscoDancers(strength,false); }catch(e){}
  }
  discoRaf=requestAnimationFrame(tick);
}
/* Auto lėta→šokiai BE MediaElementSource (jis nutildydavo).
   Naudojam WebAudio Analyser ant atskiro MediaStream, jei browser palaiko captureStream. */
function startEnergyWatch(){
  stopEnergyWatch();
  if(radioStationId!=='club') return;
  energyWatchTimer=setInterval(function(){
    if(document.visibilityState==='hidden' || !isAudioMaster() || !musicOn) return;
    if(radioStationId!=='club' || !radioIsPlaying()){ slowEnergyStreak=0; return; }
    /* Įžangoje be captureStream — vaizdas prioritetas */
    try{ if(document.body.classList.contains('cover-mode') && document.querySelector('.dd-video')) return; }catch(e){}
    var analyser=getRadioAnalyser();
    if(!analyser) return;
    try{
      if(radioAnalyserCtx && radioAnalyserCtx.state==='suspended') radioAnalyserCtx.resume();
      var buf=new Uint8Array(analyser.fftSize);
      analyser.getByteTimeDomainData(buf);
      var sum=0, peak=0;
      for(var i=0;i<buf.length;i++){
        var v=Math.abs((buf[i]-128)/128);
        sum+=v*v;
        if(v>peak) peak=v;
      }
      var rms=Math.sqrt(sum/buf.length);
      radioPeakHistory.push(rms);
      if(radioPeakHistory.length>8) radioPeakHistory.shift();
      var avg=0;
      for(var j=0;j<radioPeakHistory.length;j++) avg+=radioPeakHistory[j];
      avg/=radioPeakHistory.length;
      /* Lėta = žemas RMS ilgiau; tik jei tikrai girdim signalą */
      if(avg>0.002 && avg<0.04){
        slowEnergyStreak++;
        if(slowEnergyStreak>=SLOW_ENERGY_SECONDS){
          slowEnergyStreak=0;
          stopEnergyWatch();
          selectRadioStation('dance', true);
        }
      } else if(avg>=0.04){
        slowEnergyStreak=0;
      }
    }catch(e){}
  },1000);
}
function renderRadioChoices(){
  var el=document.getElementById('radioBadge');
  if(!el){
    el=document.createElement('div');
    el.id='radioBadge';
    el.className='radio-badge';
    document.body.appendChild(el);
  }
  /* Tik Klubas ženklelis — Šokiai auto fone, mygtuko nerodom */
  el.setAttribute('aria-label','Klubinė muzika');
  el.innerHTML='<button class="radio-choice active" type="button" data-radio="club"><span class="rb-top">klubo</span><span class="rb-mid">Bendruomenė</span></button>';
}
function setRadioBadge(){
  renderRadioChoices();
}
function selectRadioStation(id, fromAuto){
  var st=getRadioStation(id);
  if(!st) return;
  if(st.id===radioStationId && (radioIsPlaying() || radioStarting) && !fromAuto) return;
  pageAudioOk=true;
  radioArmed=true;
  musicOn=true;
  radioStationId=st.id;
  radioLabel=st.name;
  radioUrlTry=0;
  claimAudioMaster(true);
  setRadioBadge();
  hardKillRadio();
  startMusic(true);
}
document.addEventListener('click', function(ev){
  var btn=ev.target && ev.target.closest ? ev.target.closest('[data-radio]') : null;
  if(!btn) return;
  ev.preventDefault();
  selectRadioStation(btn.getAttribute('data-radio')||'club', false);
});

function startMusic(steal){
  if(stageMusicMuted()){ muteMusicForStage(); return; }
  if(deskSongOn) return;
  if(!musicOn) return;
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  var cover=isCoverMode();
  if(cover){ try{ claimAudioMaster(true); }catch(e){} }
  else if(!isAudioMaster() && !claimAudioMaster(!!steal)) return;
  if(radioStarting) return;
  var el=getRadioEl();
  if(!el) return;
  var st=getRadioStation(radioStationId);
  var url=(radioUrlTry===1 && st.fallback) ? st.fallback : st.url;
  /* JAU gyvas srautas tuo pačiu URL — NENAIKINTI (teardown = tyla). Tik unmute. */
  if(radioHasLiveStream() && radioSrcMatches(el, url)){
    radioArmed=true;
    radioLabel=st.name;
    try{ setRadioBadge(); }catch(e){}
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=(radioVolumeForCurrentState());
    }catch(e){}
    try{ var p0=el.play(); if(p0&&p0.catch) p0.catch(function(){}); }catch(e){}
    if(st.id==='club'){ try{ startEnergyWatch(); }catch(e){} }
    try{ startDiscoBeat(); }catch(e){}
    return;
  }
  radioArmed=true;
  radioStarting=true;
  shoutKillOthers();
  stopEnergyWatch();
  releaseRadioAnalyser();
  /* NENAIKINTI src jei jau tas pats URL — tik play */
  var needReload=!radioSrcMatches(el, url);
  if(needReload){
    try{
      el.pause();
      el.onplaying=null;
      el.onerror=null;
      el.removeAttribute('crossorigin');
      el.removeAttribute('src');
      el.load();
    }catch(e){}
    el.src=url;
  }
  el.volume=(radioVolumeForCurrentState());
  el.onplaying=function(){
    radioStarting=false;
    radioLabel=st.name;
    setRadioBadge();
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=(radioVolumeForCurrentState());
    }catch(e){}
    if(st.id==='club') startEnergyWatch();
    else stopEnergyWatch();
    try{ startDiscoBeat(); }catch(e){}
  };
  el.onerror=function(){
    if(radioUrlTry===0 && st.fallback){
      radioUrlTry=1;
      radioStarting=false;
      setTimeout(function(){ if(musicOn) startMusic(true); }, 200);
      return;
    }
    radioStarting=false;
    stopEnergyWatch();
    try{ stopDiscoBeat(); }catch(e){}
    if(st.id==='club'){
      radioStationId='dance';
      radioLabel='Šokiai';
      radioUrlTry=0;
      setRadioBadge();
      setTimeout(function(){ if(musicOn) startMusic(true); }, 250);
    }
  };
  function afterPlayOk(){
    radioStarting=false;
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=(radioVolumeForCurrentState());
    }catch(e){}
  }
  function playMutedFallback(){
    /* Chrome leidžia muted autoplay — srautas bufferina; gestas = garsas iškart */
    try{
      el.muted=true;
      var pm=el.play();
      if(pm && pm.then){
        pm.then(function(){ radioStarting=false; }).catch(function(){ radioStarting=false; });
      } else { radioStarting=false; }
    }catch(e){ radioStarting=false; }
  }
  try{
    el.muted=false;
    el.defaultMuted=false;
    el.removeAttribute('muted');
    var p=el.play();
    if(p && p.then){
      p.then(afterPlayOk).catch(function(){
        playMutedFallback();
      });
    } else {
      radioStarting=false;
    }
  }catch(e){
    playMutedFallback();
  }
}

function stopMusic(){
  hardKillRadio();
}

function setMusicDuck(ducking){
  var shouldDuck = !!ducking || !!vilkasStageOn;
  try{
    var ds=getDeskSongEl();
    if(ds && deskSongOn){ ds.volume = vilkasStageOn ? DESK_SONG_VOL*0.10 : (shouldDuck ? DESK_SONG_VOL*MUSIC_DUCK_RATIO : DESK_SONG_VOL); }
  }catch(e){}
  var el=getRadioEl();
  if(!el) return;
  var target = (!musicOn || deskSongOn || stageMusicMuted()) ? 0 : (vilkasStageOn ? radioTargetVol*0.10 : (shouldDuck ? radioDuckVol : radioTargetVol));
  if(radioFadeTimer) clearInterval(radioFadeTimer);
  radioFadeTimer = setInterval(function(){
    var r=getRadioEl();
    if(!r){ clearInterval(radioFadeTimer); return; }
    var cur = r.volume;
    var step = 0.018;
    if(Math.abs(cur - target) <= step){
      r.volume = target;
      clearInterval(radioFadeTimer);
    } else if(cur < target){
      r.volume = Math.min(target, cur + step);
    } else {
      r.volume = Math.max(target, cur - step);
    }
  }, 40);
}

function syncMusicBtn(){
  musicOn = true;
}
/* ---- šokėjų rotacija kas 5–10 min + fono auto-prisitaikymas pagal video ---- */
var dancerDeck=[], dancerDeckPos=0, dancerCurrentUrl='', dancerTimer=null, dancerProbed=false;
window.__DH=212;
function discoSetHue(h){
  h=((Math.round(h)%360)+360)%360; window.__DH=h;
  var f=document.getElementById('discoField'); if(!f) return;
  try{
    f.style.setProperty('--dh',h);
    f.style.setProperty('--dhA',(h+340)%360);
    f.style.setProperty('--dhB',(h+20)%360);
  }catch(e){}
}
function discoSampleHue(video){
  try{
    var c=document.createElement('canvas'); c.width=48; c.height=27;
    var x=c.getContext('2d',{willReadFrequently:true});
    x.drawImage(video,0,0,48,27);
    var d=x.getImageData(0,0,48,27).data, sh=0, ss=0;
    for(var i=0;i<d.length;i+=4){
      var r=d[i]/255,g=d[i+1]/255,b=d[i+2]/255;
      var mx=Math.max(r,g,b),mn=Math.min(r,g,b),df=mx-mn;
      if(mx<0.16||df<0.12) continue;
      var h=0;
      if(df){ if(mx===r) h=((g-b)/df)%6; else if(mx===g) h=(b-r)/df+2; else h=(r-g)/df+4; h*=60; if(h<0)h+=360; }
      var w=df*mx; sh+=h*w; ss+=w;
    }
    if(ss>0.5) discoSetHue(sh/ss);
  }catch(e){}
}
var DANCER_WHITELIST=__DANCER_URLS_JSON__;
function dancerShuffle(arr){
  for(var i=arr.length-1;i>0;i--){
    var j=Math.floor(Math.random()*(i+1));
    var tmp=arr[i]; arr[i]=arr[j]; arr[j]=tmp;
  }
  return arr;
}
function dancerCacheBust(url){
  /* STABILUS kešas vieno deploy viduje — Date.now LAUŽĖ kešą ir vėlavo kiekvienas swap.
     PAGE_BUILD keičiasi tik per deploy, todėl video kraunasi iš kešo akimirksniu. */
  var q=String(url||'').indexOf('?');
  var base=(q>=0?String(url).slice(0,q):String(url));
  var ver='1';
  try{ ver=String(window.PAGE_BUILD||document.querySelector('meta[name="build"]')?.content||'1').slice(0,24); }catch(e){}
  return base+'?v='+encodeURIComponent(ver);
}
var dancerPreloadEl=null, dancerPreloadUrl='';
function dancerPreloadNext(){
  try{
    if(!document.body.classList.contains('cover-mode')) return;
    var nxt=dancerDeck[dancerDeckPos]||'';
    if(!nxt||nxt===dancerCurrentUrl||nxt===dancerPreloadUrl) return;
    if(!dancerPreloadEl){
      dancerPreloadEl=document.createElement('video');
      dancerPreloadEl.muted=true; dancerPreloadEl.loop=true;
      dancerPreloadEl.playsInline=true; dancerPreloadEl.preload='auto';
      dancerPreloadEl.setAttribute('playsinline',''); dancerPreloadEl.setAttribute('muted','');
      dancerPreloadEl.style.display='none';
      try{document.body.appendChild(dancerPreloadEl);}catch(e){}
    }
    dancerPreloadUrl=nxt;
    dancerPreloadEl.src=dancerCacheBust(nxt);
    try{ dancerPreloadEl.load(); }catch(e){}
  }catch(e){}
}
setInterval(function(){ try{ dancerPreloadNext(); }catch(e){} }, 8000);
function dancerSaveState(){
  try{
    localStorage.setItem('dancer_deck', JSON.stringify(dancerDeck||[]));
    localStorage.setItem('dancer_pos', String(dancerDeckPos||0));
  }catch(e){}
}
function dancerLoadState(){
  try{
    var raw=localStorage.getItem('dancer_deck')||'';
    var pos=parseInt(localStorage.getItem('dancer_pos')||'0',10)||0;
    if(!raw) return false;
    var arr=JSON.parse(raw);
    if(!arr||!arr.length) return false;
    /* palikti tik whitelist video — apsauga nuo senų/pašalintų URL */
    var ok=[];
    for(var i=0;i<arr.length;i++){ if(DANCER_WHITELIST.indexOf(arr[i])>=0) ok.push(arr[i]); }
    if(!ok.length) return false;
    /* jei deck trumpas (sena versija) — pratęsti trūkstamais be dublio */
    if(ok.length<DANCER_WHITELIST.length){
      var rest=[];
      for(var k=0;k<DANCER_WHITELIST.length;k++){ if(ok.indexOf(DANCER_WHITELIST[k])<0) rest.push(DANCER_WHITELIST[k]); }
      ok=ok.concat(dancerShuffle(rest));
    }
    if(pos<0) pos=0; if(pos>ok.length) pos=ok.length;
    dancerDeck=ok; dancerDeckPos=pos;
    return true;
  }catch(e){ return false; }
}
function dancerUpdateCount(){
  try{
    var el=document.getElementById('dancerCount'); if(!el) return;
    var total=(typeof DANCER_WHITELIST!=='undefined'&&DANCER_WHITELIST.length)?DANCER_WHITELIST.length:15;
    var n=dancerDeckPos||0; if(n<1) n=1; if(n>total) n=total;
    el.textContent=n+'/'+total;
  }catch(e){}
}
function dancerRefillDeck(excludeBase){
  dancerDeck=dancerShuffle(DANCER_WHITELIST.slice());
  dancerDeckPos=0;
  if(excludeBase&&dancerDeck.length>1&&dancerDeck[0]===excludeBase){
    for(var i=1;i<dancerDeck.length;i++){
      if(dancerDeck[i]!==excludeBase){
        var t=dancerDeck[0]; dancerDeck[0]=dancerDeck[i]; dancerDeck[i]=t;
        break;
      }
    }
  }
  dancerSaveState();
}
function dancerTakeNext(excludeBase){
  if(!dancerDeck.length||dancerDeckPos>=dancerDeck.length) dancerRefillDeck(excludeBase||'');
  if(excludeBase&&dancerDeck.length>1&&dancerDeck[dancerDeckPos]===excludeBase){
    dancerDeckPos++;
    if(dancerDeckPos>=dancerDeck.length) dancerRefillDeck(excludeBase);
  }
  return dancerDeck[dancerDeckPos]||'';
}
function dancerCommitNext(){ dancerDeckPos++; dancerSaveState(); dancerUpdateCount(); }
/* Serveris nusprendžia šokėją — VISI ekranai tą pačią (PC = telefonas). */
var dancerServerSeenAt=0;
function dancerBase(u){ return String(u||'').split('?')[0]; }
function applyServerDancer(st){
  try{
    var d=st&&st.dancer?st.dancer:null;
    if(!d||!d.url) return;
    if(!document.body.classList.contains('cover-mode')) return;
    dancerServerSeenAt=Date.now();
    var base=String(d.url);
    if(dancerBase(dancerCurrentUrl)===dancerBase(base)){
      try{
        var el=document.getElementById('dancerCount');
        if(el&&d.n) el.textContent=d.n+'/'+(d.total||DANCER_WHITELIST.length);
      }catch(e){}
      return;
    }
    if(dancerApplyNow(base)){
      try{
        var idx=(typeof d.idx==='number')?d.idx:-1;
        if(idx<0){ for(var i=0;i<DANCER_WHITELIST.length;i++){ if(DANCER_WHITELIST[i]===base){ idx=i; break; } } }
        if(idx>=0){
          var order=[];
          for(var k=1;k<=DANCER_WHITELIST.length;k++){ order.push(DANCER_WHITELIST[(idx+k)%DANCER_WHITELIST.length]); }
          dancerDeck=order; dancerDeckPos=0; dancerSaveState();
        }
        var el2=document.getElementById('dancerCount');
        if(el2&&d.n) el2.textContent=d.n+'/'+(d.total||DANCER_WHITELIST.length);
        dancerPreloadUrl='';
        setTimeout(function(){ dancerPreloadNext(); },800);
      }catch(e){}
    }
  }catch(e){}
}
window.addEventListener('keydown',function(e){
  try{ if(e&&e.key==='F5'){ navigator.sendBeacon('/api/dancer/next'); } }catch(_){}
});
function dancerApplyNow(baseUrl,retry){
  if(!baseUrl) return false;
  var v=document.querySelector('.dd-video'); if(!v) return false;
  var target=dancerCacheBust(baseUrl);
  try{ v.src=target; v.load(); var p=v.play(); if(p&&p.catch)p.catch(function(){}); }catch(e){
    if(!retry) return dancerApplyNow(baseUrl,true);
    return false;
  }
  dancerCurrentUrl=baseUrl;
  try{ localStorage.setItem('dancer_last', baseUrl); }catch(e){}
  try{ dancerUpdateCount(); }catch(e){}
  setTimeout(function(){ try{ discoSampleHue(v); }catch(e){} },1200);
  return true;
}
function dancerEnsurePlaying(){
  if(dancerCurrentUrl) return;
  fetch('/api/dancer',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
    applyServerDancer({dancer:d&&d.dancer});
    if(!dancerCurrentUrl){
      var next=dancerTakeNext('');
      if(next&&dancerApplyNow(next)) dancerCommitNext();
    }
  }).catch(function(){
    if(dancerCurrentUrl) return;
    var next=dancerTakeNext('');
    if(next&&dancerApplyNow(next)) dancerCommitNext();
  });
}
function dancerOnPoolReady(){
  /* Transliacija VIENA: šokėją parenka serveris (/photos dance_club).
     PC ir telefonas seka tą patį URL — ne localStorage deck. */
  dancerEnsurePlaying();
}
function dancerProbePool(){
  if(dancerProbed) return;
  dancerProbed=true;
  dancerOnPoolReady();
  /* NEBE-probe'inam visų 15 iš karto — tai ir vėlino startą (15x lygiagretus fetch).
     Užtenka preload next; whitelist jau patikrintas serveryje. */
  try{ setTimeout(function(){ dancerPreloadNext(); }, 2500); }catch(e){}
}
function dancerSchedule(){
  if(dancerTimer){ try{clearTimeout(dancerTimer);}catch(e){} dancerTimer=null; }
  dancerTimer=setTimeout(dancerSwap,(2+Math.random()*1)*60000);
}
function dancerSwap(){
  if(!document.body.classList.contains('cover-mode')||document.visibilityState==='hidden'){ dancerSchedule(); return; }
  var v=document.querySelector('.dd-video'); if(!v){ dancerSchedule(); return; }
  if(v.dataset.swapBusy==='1'){ dancerSchedule(); return; }
  /* NEkeisti lokaliai — visiems viena šokėja iš serverio */
  fetch('/api/dancer',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
    applyServerDancer({dancer:d&&d.dancer});
    dancerSchedule();
  }).catch(function(){ dancerSchedule(); });
}
function startDancerRotation(){
  dancerProbePool();
  dancerEnsurePlaying();
  try{ discoSetHue(212); }catch(e){}
  if(dancerTimer) return;
  dancerSchedule();
}
setTimeout(function(){ try{ dancerProbePool(); }catch(e){} },4000);
var introMediaRetry=null;
function ensureIntroMedia(steal){
  if(!document.body.classList.contains('cover-mode')) return;
  try{ releaseRadioAnalyser(); }catch(e){} /* atlaisvinti captureStream — vaizdas nestabdytų */
  try{ if(!discoRaf) startDiscoBeat(); }catch(e){}
  try{ if(typeof startDancerRotation==='function') startDancerRotation(); }catch(e){}
  try{ keepDancerVideoAlive(); }catch(e){}
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  radioArmed=true;
  musicOn=true;
  claimAudioMaster(true);
  try{ setRadioBadge(); }catch(e){}
  try{ keepRadioAlive(); }catch(e){}
  if(radioHasLiveStream() && !discoRaf){
    try{ startDiscoBeat(); }catch(e){}
  }
  if(introMediaRetry) return;
  introMediaRetry=setInterval(function(){
    if(!document.body.classList.contains('cover-mode')){
      clearInterval(introMediaRetry); introMediaRetry=null; return;
    }
    try{ if(typeof startDancerRotation==='function') startDancerRotation(); }catch(e){}
    if(document.visibilityState==='hidden') return;
    pageAudioOk=true;
    claimAudioMaster(true);
    try{ if(!discoRaf) startDiscoBeat(); }catch(e){}
    try{ keepRadioAlive(); }catch(e){}
    if(radioHasLiveStream()){
      try{ if(!discoRaf) startDiscoBeat(); }catch(e){}
    }
  }, 1200);
}
function stopIntroMediaRetry(){
  if(introMediaRetry){ clearInterval(introMediaRetry); introMediaRetry=null; }
}
function syncVoiceBtn(){
  var btn=document.getElementById('btnVoice');
  if(!btn) return;
  btn.textContent = voiceOn ? 'Balsas ON' : 'Balsas OFF';
  btn.classList.toggle('on', voiceOn);
}
var _vb = document.getElementById('btnVoice');
if(_vb) _vb.onclick=function(){
  unlockAudio(); voiceOn=!voiceOn; localStorage.setItem('host_voice', voiceOn?'1':'0'); syncVoiceBtn();
  if(voiceOn) queueAnnounce('Vilkas grįžo! Balsas įjungtas, kūjis paruoštas!');
};
syncMusicBtn(); syncVoiceBtn();
voiceOn = true; // balsas visada ON — mygtuko UI nėra

/* Įžanga: HTML autoplay muted = srautas iškart; kick bando unmute; gestas = garsas. */
(function bootCoverAudioHard(){
  try{ localStorage.removeItem(AUDIO_MASTER_KEY); }catch(e){}
  try{ claimAudioMaster(true); }catch(e){}
  function kick(){
    if(!document.body.classList.contains('cover-mode')) return;
    pageAudioOk=true; radioArmed=true; musicOn=true;
    try{ claimAudioMaster(true); }catch(e){}
    try{ ensureIntroMedia(true); }catch(e){}
    try{ keepRadioAlive(); }catch(e){}
  }
  kick();
  setTimeout(kick, 150);
  setTimeout(kick, 500);
  setTimeout(kick, 1200);
  setTimeout(kick, 2500);
})();

// ---------- konfeti ----------
var confettiCanvas = document.getElementById('confettiCanvas');
var cctx = confettiCanvas.getContext('2d');
var confettiParticles = [];
function resizeConfetti(){ confettiCanvas.width = window.innerWidth; confettiCanvas.height = window.innerHeight; }
window.addEventListener('resize', resizeConfetti); resizeConfetti();
var confettiColors = ['#ff7a33','#ffb347','#e3b23c','#4caf7d','#f3ead9'];
function fireworkBurst(cx, cy, count){
  for(var i=0;i<count;i++){
    var ang = (Math.PI*2)*(i/count) + Math.random()*0.3;
    var speed = 4+Math.random()*7;
    confettiParticles.push({
      x: cx, y: cy, vx: Math.cos(ang)*speed, vy: Math.sin(ang)*speed,
      grav: 0.13, size: 4+Math.random()*5, color: confettiColors[i%confettiColors.length],
      rot: Math.random()*360, vrot: (Math.random()-0.5)*14, life: 0
    });
  }
}
function launchConfetti(){
  confettiParticles = [];
  var w = confettiCanvas.width;
  fireworkBurst(w*0.28, confettiCanvas.height*0.32, 60);
  setTimeout(function(){ fireworkBurst(w*0.72, confettiCanvas.height*0.28, 60); }, 260);
  setTimeout(function(){ fireworkBurst(w*0.5, confettiCanvas.height*0.22, 70); }, 520);
  // ir sviesios krentancios juostelas is virsaus, kaip anksciau, papildomai
  for(var i=0;i<70;i++){
    confettiParticles.push({
      x: Math.random()*w, y: -20-Math.random()*200,
      vx: (Math.random()-0.5)*3, vy: 2+Math.random()*4, grav: 0,
      size: 5+Math.random()*6, color: confettiColors[i%confettiColors.length],
      rot: Math.random()*360, vrot: (Math.random()-0.5)*10, life: 0
    });
  }
  confettiCanvas.classList.add('show');
  var start = Date.now();
  function frame(){
    cctx.clearRect(0,0,confettiCanvas.width,confettiCanvas.height);
    var elapsed = Date.now()-start;
    confettiParticles.forEach(function(p){
      p.x+=p.vx; p.y+=p.vy; p.vy += (p.grav||0); p.rot+=p.vrot; p.life++;
      var alpha = p.grav ? Math.max(0, 1-p.life/70) : 1;
      cctx.save(); cctx.globalAlpha = alpha; cctx.translate(p.x,p.y); cctx.rotate(p.rot*Math.PI/180);
      cctx.fillStyle = p.color; cctx.fillRect(-p.size/2,-p.size/2,p.size,p.size*0.6);
      cctx.restore();
    });
    if(elapsed < 3800){ requestAnimationFrame(frame); }
    else { confettiCanvas.classList.remove('show'); cctx.clearRect(0,0,confettiCanvas.width,confettiCanvas.height); }
  }
  frame();
}

var myName = localStorage.getItem('vardas') || '';
var myNickname = localStorage.getItem('slapyvardis') || '';
var myContact = localStorage.getItem('kontaktas') || '';
var myPhone = localStorage.getItem('telefonas') || '';
var myPayMethod = localStorage.getItem('mokejimo_budas') || '';
var myPid = localStorage.getItem('pid') || '';
(function bootBuyerFlag(){
  try{
    var q=new URLSearchParams(location.search);
    var force = q.get('buyer')==='1' || q.get('as')==='pirkejas' || q.get('fresh')==='play' || q.get('fresh')==='demo';
    var suppliedPid = q.get('pid') || '';
    if(force){
      localStorage.setItem('aukcionas_buyer','1');
      /* Asmeninė testo nuoroda turi jau užregistruoto dalyvio PID. */
      if(suppliedPid){
        myPid=suppliedPid;
        localStorage.setItem('pid',myPid);
      } else {
        localStorage.removeItem('pid');
        myPid = '';
      }
      if(!localStorage.getItem('vardas') || localStorage.getItem('vardas')==='Mindaugas') localStorage.setItem('vardas','Mindaugas');
      if(!localStorage.getItem('slapyvardis')) localStorage.setItem('slapyvardis','Mindaugas');
      if(!localStorage.getItem('kontaktas')) localStorage.setItem('kontaktas','mindaugasbusiness@gmail.com');
      if(!localStorage.getItem('telefonas')) localStorage.setItem('telefonas','+37066331913');
      if(!localStorage.getItem('mokejimo_budas')) localStorage.setItem('mokejimo_budas','paypal');
      myName = localStorage.getItem('vardas') || 'Mindaugas';
      myNickname = localStorage.getItem('slapyvardis') || 'Mindaugas';
      myContact = localStorage.getItem('kontaktas') || 'mindaugasbusiness@gmail.com';
      myPhone = localStorage.getItem('telefonas') || '+37066331913';
      myPayMethod = localStorage.getItem('mokejimo_budas') || 'paypal';
    }
  }catch(e){}
})();
var els = {};
['lotTag','viewerCount','artWrap','artEmpty','itemBody','itemTitle','itemMeta','descText','priceNum','bidderLine','joinForm','joinFormTitle','nameInput','nicknameInput','contactInput','phoneInput','joinBtn','regNote','regClosedNote','bidBtn','bidLabel','timerNum','timerCircle','hint','soldBanner','soldName','soldPrice','payBox','payTotal','payWait','payPrivate','payPrivLabel','payPrivMail','payPrivHint','feedList','pastBox','pastList','countdownOverlay','countdownNum','celebrateOverlay','celebrateName','celebratePrice','celebrateClose','lockBanner'].forEach(function(id){els[id]=document.getElementById(id);});
if(els.nameInput && myName) els.nameInput.value = myName;
if(els.nicknameInput && myNickname) els.nicknameInput.value = myNickname;
if(els.contactInput && myContact) els.contactInput.value = myContact;
if(els.phoneInput && myPhone) els.phoneInput.value = myPhone;
(function restorePayRadio(){
  if(!myPayMethod) return;
  var r=document.querySelector('input[name="payMethod"][value="'+myPayMethod+'"]');
  if(r) r.checked=true;
})();
function selectedPayMethod(){
  var r=document.querySelector('input[name="payMethod"]:checked');
  return r ? r.value : '';
}
function syncRegPanel(){
  var done = document.getElementById('ppDone');
  var doneMsg = document.getElementById('ppDoneMsg');
  var panel = document.getElementById('participantsPanel');
  if(myPid){
    if(panel) panel.classList.add('registered');
    if(panel) panel.classList.remove('reg-collapsed');
    if(els.joinForm) els.joinForm.style.display='none';
    if(done) done.style.display='flex';
    if(doneMsg) doneMsg.textContent='Tu jau užsiregistravęs kaip '+(myNickname||'Mindaugas')+'. Kaina kelti — kai bus gyvas lotas.';
  } else {
    if(panel) panel.classList.remove('registered');
    if(panel && window.innerWidth<=640 && !panel.dataset.regOpened) panel.classList.add('reg-collapsed');
    if(els.joinForm) els.joinForm.style.display='flex';
    if(els.joinFormTitle) els.joinFormTitle.textContent='1. Registracija';
    if(done) done.style.display='none';
  }
}
syncRegPanel();
(function(){
  var btn=document.getElementById('ppChangeReg');
  if(!btn) return;
  btn.onclick=function(){
    myPid=''; myName=''; myNickname=''; myContact=''; myPhone=''; myPayMethod='';
    try{
      localStorage.removeItem('pid');
      localStorage.removeItem('name');
      localStorage.removeItem('nickname');
      localStorage.removeItem('contact');
      localStorage.removeItem('telefonas');
      localStorage.removeItem('pay_method');
    }catch(e){}
    if(els.nameInput) els.nameInput.value='';
    if(els.nicknameInput) els.nicknameInput.value='';
    if(els.contactInput) els.contactInput.value='';
    if(els.phoneInput) els.phoneInput.value='';
    syncRegPanel();
  };
})();
if(els.joinFormTitle) els.joinFormTitle.onclick=function(){
  var panel=document.getElementById('participantsPanel');
  if(!panel || myPid) return;
  panel.dataset.regOpened='1';
  panel.classList.toggle('reg-collapsed');
};
function registerBuyer(done){
  if(state && state.public_registration_open===false){ if(done) done(false); return; }
  var name = (myName||'Mindaugas').slice(0,80);
  var nickname = (myNickname||'Mindaugas').slice(0,24);
  var contact = (myContact||'mindaugasbusiness@gmail.com').slice(0,60);
  var phone = (myPhone||'+37066331913').slice(0,32);
  var pay_method = (myPayMethod||'paypal');
  fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,nickname:nickname,contact:contact,phone:phone,pay_method:pay_method})})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d && d.pid){
        myPid=d.pid; myName=name; myNickname=nickname; myContact=contact; myPhone=phone; myPayMethod=pay_method;
        try{
          localStorage.setItem('pid', myPid);
          localStorage.setItem('vardas', myName);
          localStorage.setItem('slapyvardis', myNickname);
          localStorage.setItem('kontaktas', myContact);
          localStorage.setItem('telefonas', myPhone);
          localStorage.setItem('mokejimo_budas', myPayMethod);
          localStorage.setItem('aukcionas_buyer','1');
        }catch(e){}
        syncRegPanel();
      }
      if(done) done(!!(d && d.pid));
    })
    .catch(function(){ if(done) done(false); });
}
function ensureBuyerSession(done){
  var want=false;
  try{ want = localStorage.getItem('aukcionas_buyer')==='1'; }catch(e){}
  /* Nuorodoje esantis PID jau yra užregistruotas dalyvis: jo neperrašome. */
  if(myPid){ syncRegPanel(); if(done) done(); return; }
  if(!want){ if(done) done(); return; }
  /* Jei PID nėra, sukurkime naują pirkėjo sesiją. */
  myPid = '';
  try{ localStorage.removeItem('pid'); }catch(e){}
  registerBuyer(function(){ if(done) done(); });
}
function fmt(n){return (n||0).toLocaleString('lt-LT',{minimumFractionDigits:2,maximumFractionDigits:2});}
function stepFor(p){return 1;}
function timeStr(ms){var s=Math.max(0,Math.ceil(ms/1000)),m=Math.floor(s/60),r=s%60;return m+':'+(r<10?'0':'')+r;}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function applyAuctionLock(locked, msg){
  document.body.classList.toggle('auction-locked', !!locked);
  if(els.lockBanner){
    if(locked){
      els.lockBanner.classList.add('show');
      if(msg) els.lockBanner.innerHTML = '<b>Aukcionas ruošiamas</b> — '+esc(msg);
    } else {
      els.lockBanner.classList.remove('show');
    }
  }
  if(els.joinBtn) els.joinBtn.disabled = false;
  if(locked){
    if(els.bidBtn){
      els.bidBtn.disabled = true;
      els.bidLabel.textContent = 'KELTI KAINĄ +1 €';
    }
    if(els.payBox) els.payBox.classList.remove('show');
    if(els.soldBanner) els.soldBanner.classList.remove('show');
    if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
  }
}
function applyPublicRegistration(open, msg){
  var on = open !== false;
  document.body.classList.toggle('reg-closed', !on);
  var hideIds=['nameInput','nicknameInput','contactInput','phoneInput','joinBtn','payMethodOpts'];
  hideIds.forEach(function(id){ var el=els[id]||document.getElementById(id); if(el) el.style.display = on ? '' : 'none'; });
  if(els.joinFormTitle) els.joinFormTitle.textContent = on ? '1. Registracija' : 'Registracija uždaryta';
  if(els.regNote) els.regNote.style.display = on ? '' : 'none';
  if(els.regClosedNote){
    els.regClosedNote.style.display = on ? 'none' : 'block';
    if(!on) els.regClosedNote.textContent = msg || 'Registracija uždaryta — Vilkas mokosi su imitaciniais pirkėjais.';
  }
  if(els.joinBtn) els.joinBtn.disabled = !on;
}

els.joinBtn.onclick=function(){
  if(state && state.public_registration_open===false){
    applyPublicRegistration(false, state.public_reg_closed_msg||'');
    if(els.regClosedNote) els.regClosedNote.textContent = state.public_reg_closed_msg || 'Registracija uždaryta.';
    return;
  }
  unlockAudio();
  if(musicOn) resumeRadio();
  var name=els.nameInput.value.trim(), nickname=els.nicknameInput.value.trim(), contact=els.contactInput.value.trim();
  var phone=(els.phoneInput?els.phoneInput.value:'').trim();
  var pay_method=selectedPayMethod();
  if(!name){els.regNote.textContent='Įvesk vardą ir pavardę.';return;}
  if(!(contact.indexOf('@')>1 && contact.indexOf('.',contact.indexOf('@'))>contact.indexOf('@'))){
    els.regNote.textContent='Įvesk el. paštą — ten gausi mokėjimo instrukcijas.';return;
  }
  if((phone.replace(/\D/g,'')).length<8){
    els.regNote.textContent='Įvesk telefono numerį (kad galėtume susisiekti).';return;
  }
  if(!pay_method){els.regNote.textContent='Pažymėk, kuo atsiskaitysi: PayPal, Skrill, Neteller arba Paysafe.';return;}
  els.joinBtn.disabled=true;
  els.regNote.textContent='Registruojama…';
  fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,nickname:nickname,contact:contact,phone:phone,pay_method:pay_method})})
    .then(function(r){
      if(!r.ok) return r.json().then(function(d){ throw new Error(d.detail || 'Registracija nepavyko'); });
      return r.json();
    }).then(function(d){
      var isExtraParticipant=!!myPid;
      var publicName=(d && d.public_name) || nickname || name.split(/\s+/)[0] || name;
      if(!isExtraParticipant){
        myName=name; myNickname=publicName; myContact=contact; myPhone=phone; myPayMethod=pay_method; myPid=d.pid;
        localStorage.setItem('vardas',name); localStorage.setItem('slapyvardis',myNickname); localStorage.setItem('kontaktas',contact); localStorage.setItem('telefonas',phone); localStorage.setItem('mokejimo_budas',pay_method); localStorage.setItem('pid',myPid);
      }
      els.regNote.textContent='';
      syncRegPanel();
      // Iš karto — sąrašas + skaičius (optimistiškai, tada poll)
      if(state){
        state.participant_count = (state.participant_count||0)+1;
        state.participant_names = [publicName].concat((state.participant_names||[]).filter(function(n){ return n!==publicName; }));
        renderParticipants();
      }
      if(isExtraParticipant){
        els.nameInput.value=''; els.nicknameInput.value=''; els.contactInput.value=''; if(els.phoneInput) els.phoneInput.value='';
        document.querySelectorAll('input[name="payMethod"]').forEach(function(x){ x.checked=false; });
        els.regNote.textContent='Dalyvis '+publicName+' užregistruotas ('+pay_method+').';
      }
      els.joinBtn.disabled=false;
      poll();
    }).catch(function(e){
      els.joinBtn.disabled=false;
      els.regNote.textContent = e.message || 'Registracija nepavyko';
    });
};
var state=null;
var lastLotId = null;
var lastStatus = null;
var lastCountdownInt = null;
var locallyAnnouncedBid = null;
els.bidBtn.onclick=function(){
  if(!state || !state.lot) return;
  if(state.auction_locked){
    applyAuctionLock(true, state.auction_lock_msg);
    return;
  }
  var lot=state.lot;
  if(lot.status!=='live') return;
  if(lot.starts_at && lot.starts_at*1000 > Date.now()) return;
  unlockAudio();
  if(musicOn) resumeRadio();
  els.bidBtn.disabled=true;
  function sendBid(retried){
    if(!myPid){
      registerBuyer(function(ok){
        if(!ok){ poll(); return; }
        sendBid(true);
      });
      return;
    }
    fetch('/api/bid',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:myPid,nickname:myNickname})})
      .then(function(r){
        if(r.ok) return r.json();
        if((r.status===403) && !retried){
          myPid=''; try{ localStorage.removeItem('pid'); }catch(e){}
          return new Promise(function(resolve,reject){
            registerBuyer(function(ok){
              if(!ok){ reject(new Error('reg')); return; }
              fetch('/api/bid',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:myPid,nickname:myNickname})})
                .then(function(r2){ if(!r2.ok) throw new Error('bid'); return r2.json(); })
                .then(resolve).catch(reject);
            });
          });
        }
        throw new Error('bid_'+r.status);
      })
      .then(function(d){
        /*
          Pirmas statymas negali laukti poll(): naujo loto pirmas įrašas
          anksčiau būdavo palaikomas istorija ir nutylimas.
        */
        if(d && d.ok && !d.already){
          locallyAnnouncedBid={name:myNickname, amount:Number(d.current_price)};
        }
        poll();
      })
      .catch(function(){ poll(); });
  }
  sendBid(false);
};
function closeCelebrate(){
  if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
  try{clearTimeout(window._celebrateAutoClose);}catch(e){}
}
els.celebrateClose.onclick=closeCelebrate;
var _celX=document.getElementById('celebrateCloseX');
if(_celX) _celX.onclick=closeCelebrate;

var payBoxUserClosed=false;
var _payBoxClose=document.getElementById('payBoxClose');
if(_payBoxClose) _payBoxClose.onclick=function(){
  payBoxUserClosed=true;
  if(els.payBox) els.payBox.classList.remove('show');
};

(function initPayBadges(){
  var PAY={
    paypal:{name:'PayPal',
      hint:'Po laimėjimo mokėjimo el. paštą gausite į savo registruotą el. paštą. Viešai mokėjimo adresai nerodomi.'},
    skrill:{name:'Skrill',
      hint:'Po laimėjimo Skrill mokėjimo instrukcijas gausite į savo el. paštą. Viešai adresai nerodomi.'},
    neteller:{name:'Neteller',
      hint:'Po laimėjimo Neteller mokėjimo instrukcijas gausite į savo el. paštą. Viešai adresai nerodomi.'},
    paysafe:{name:'Paysafe',
      hint:'Po laimėjimo Paysafe mokėjimo instrukcijas gausite į savo el. paštą. PIN niekada nesiųskite.'}
  };
  var detail=document.getElementById('payStripDetail');
  var nameEl=document.getElementById('psdName');
  var hintEl=document.getElementById('psdHint');
  function closePayStripDetail(){
    if(!detail) return;
    detail.classList.remove('on');
    document.querySelectorAll('.pay-badge').forEach(function(b){ b.style.outline=''; });
  }
  var _psdClose=document.getElementById('payStripDetailClose');
  if(_psdClose) _psdClose.onclick=function(ev){ if(ev){ev.preventDefault();ev.stopPropagation();} closePayStripDetail(); };
  (function(){
    var panel=document.getElementById('aqrPanel');
    var toggle=document.getElementById('aqrToggle');
    var close=document.getElementById('aqrClose');
    function closeRules(){ if(panel) panel.classList.remove('open'); }
    if(toggle) toggle.onclick=function(ev){
      if(ev){ev.preventDefault();ev.stopPropagation();}
      closePayStripDetail();
      if(panel) panel.classList.toggle('open');
    };
    if(close) close.onclick=function(ev){ if(ev){ev.preventDefault();ev.stopPropagation();} closeRules(); };
  })();
  document.querySelectorAll('.pay-badge[data-pay]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var p=PAY[btn.getAttribute('data-pay')];
      if(!p||!detail) return;
      nameEl.textContent=p.name+' — privatūs mokėjimai';
      hintEl.textContent=p.hint;
      detail.classList.add('on');
      document.querySelectorAll('.pay-badge').forEach(function(b){ b.style.outline=''; });
      btn.style.outline='2px solid #39ff6a';
      var radio=document.querySelector('input[name="payMethod"][value="'+btn.getAttribute('data-pay')+'"]');
      if(radio && !myPid) radio.checked=true;
    });
  });
})();

function loadWinnerPayment(){
  if(!els.payPrivate) return;
  if(!myPid){
    if(els.payWait) els.payWait.style.display='block';
    els.payPrivate.classList.remove('show');
    return;
  }
  fetch('/api/my_payment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:myPid})})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d && d.winner && d.pay_email){
        if(els.payWait) els.payWait.style.display='none';
        els.payPrivate.classList.add('show');
        if(els.payPrivLabel) els.payPrivLabel.textContent='Mokėkite per '+d.pay_label+' į:';
        if(els.payPrivMail) els.payPrivMail.textContent=d.pay_email;
        if(els.payPrivHint) els.payPrivHint.textContent=d.pay_hint||'';
      } else {
        if(els.payWait){
          els.payWait.style.display='block';
          els.payWait.textContent=(d && d.message) || 'Mokėjimo el. paštai viešai nerodomi. Laimėtojas gaus instrukcijas į savo el. paštą.';
        }
        els.payPrivate.classList.remove('show');
      }
    }).catch(function(){});
}

function renderParticipants(){
  var n = (state && state.participant_count) || 0;
  var names = (state && state.participant_names) || [];
  var c = document.getElementById('ppCount');
  var list = document.getElementById('ppList');
  if(c) c.textContent = n + (n===1 ? ' dalyvis' : ' dalyvių');
  if(!list) return;
  if(!names.length){
    list.innerHTML = '<div class="pp-empty">Kol kas nieko</div>';
    return;
  }
  var me = myNickname || '';
  list.innerHTML = names.map(function(name){
    var cls = (me && name===me) ? 'pp-name me' : 'pp-name';
    return '<div class="'+cls+'">'+esc(name)+'</div>';
  }).join('');
  // naujausią (pirmą) matyti viršuje
  list.scrollTop = 0;
  syncRegPanel();
}
function render(){
  setVilkasStageFromState(state);
  try{
    var wasPr=practiceModeOn;
    practiceModeOn=!!(state && state.practice_bots);
    syncPracticeMusicLevels();
    if(practiceModeOn && vilkasStageOn){
      try{ musicOn=true; radioArmed=true; pageAudioOk=true; }catch(e0){}
      if(typeof isAudioMaster==='function' && isAudioMaster() && typeof keepRadioAlive==='function') keepRadioAlive();
      else if(typeof makeRadioAudibleNow==='function') makeRadioAudibleNow();
    } else if(wasPr && !practiceModeOn && typeof keepRadioAlive==='function'){
      try{ keepRadioAlive(); }catch(e1){}
    }
  }catch(e){}
  try{ applyDeskSong(state); }catch(e){}
  try{ applyServerDancer(state); }catch(e){}
  var lot=state.lot;
  applyAuctionLock(!!state.auction_locked, state.auction_lock_msg || '');
  applyPublicRegistration(state.public_registration_open!==false, state.public_reg_closed_msg||'');
  renderParticipants();
  if(els.viewerCount) els.viewerCount.textContent=state.participant_count+(state.participant_count===1?' dalyvis':' dalyvių');
  /* Įžangos viršelis: be prekių/scenos iki Vilko ON */
  if(!isVilkasStageOn() || !lot){
    if(els.lotTag)els.lotTag.textContent= isVilkasStageOn() ? 'LOTŲ KOL KAS NĖRA' : 'ĮŽANGA';
    if(els.artEmpty)els.artEmpty.style.display='none';
    els.itemBody.style.display='none';
    els.countdownOverlay.style.display='none';
    var mp=document.getElementById('mainPanel'); if(mp) mp.classList.add('empty-lot');
    var img0=document.getElementById('artPhoto'); if(img0) img0.style.display='none';
    if(els.bidBtn){
      els.bidBtn.disabled=true;
      els.bidLabel.textContent = myPid ? 'KELTI KAINĄ +1 €' : 'REGISTRUOKIS';
    }
    renderPast();
    renderQueueRail();
    return;
  }
  var mp2=document.getElementById('mainPanel'); if(mp2) mp2.classList.remove('empty-lot');
  els.artEmpty.style.display='none'; els.itemBody.style.display='block';
  if(els.lotTag) els.lotTag.textContent='LOTAS #'+String(lot.lot_number).padStart(3,'0')+(lot.status==='ended' ? ' · PARDUOTA' : ' · GYVAI');
  els.itemTitle.textContent=lot.title||'—';
  els.itemMeta.innerHTML='Siuntimas <b>'+fmt(lot.shipping)+' €</b>';
  els.descText.textContent=lot.description||'';
  els.priceNum.innerHTML=fmt(lot.current_price)+'<small>€</small>';
  var img=document.getElementById('artPhoto');
  if(lot.photo_file){ if(!img){img=document.createElement('img');img.id='artPhoto';els.artWrap.insertBefore(img,els.artEmpty);} img.src='/photos/'+lot.photo_file; img.style.display='block';}
  else if(img){img.style.display='none';}

  var celebrating = false;
  if(state.auction_locked){
    els.soldBanner.classList.remove('show');
    els.payBox.classList.remove('show');
    els.celebrateOverlay.classList.remove('show');
    els.bidBtn.disabled=true;
    els.bidLabel.textContent='KELTI KAINĄ +1 €';
    els.bidderLine.innerHTML = 'Žiūrėti galima — pirkimas bus atidarytas, kai viską sutvarkysime.';
  } else if(lot.status==='ended'){
    els.soldBanner.classList.add('show'); els.soldName.textContent=lot.current_bidder||'—'; els.soldPrice.textContent=fmt(lot.current_price)+' €';
    els.bidBtn.disabled=true; els.bidLabel.textContent='Aukcionas baigtas';
    if(lot.current_bidder){
      if(!payBoxUserClosed) els.payBox.classList.add('show');
      else els.payBox.classList.remove('show');
      els.payTotal.textContent = fmt(lot.current_price + (lot.shipping||0)) + ' €';
      loadWinnerPayment();
    } else {
      els.payBox.classList.remove('show');
      if(els.payPrivate) els.payPrivate.classList.remove('show');
    }
    if(lastStatus!=='ended' && lot.current_bidder){
      celebrating = true;
      els.celebrateName.textContent = lot.current_bidder;
      els.celebratePrice.textContent = fmt(lot.current_price)+' €';
      els.celebrateOverlay.classList.add('show');
      launchConfetti();
      clearTimeout(window._celebrateAutoClose);
      window._celebrateAutoClose=setTimeout(function(){
        if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
      }, 4200);
    }
  } else {
    /* Naujas live lotas — nuimti seną PARDUOTA langą, kad neuždengtų +1 € */
    payBoxUserClosed=false;
    if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
    els.soldBanner.classList.remove('show');
    els.payBox.classList.remove('show');
    els.bidderLine.innerHTML = lot.current_bidder ? ('Šiuo metu siūlo <b>'+esc(lot.current_bidder)+'</b>') : 'Dar niekas nesiūlė kainos — būk pirmas.';
    var inCountdown = lot.starts_at && (lot.starts_at*1000 > Date.now());
    if(inCountdown || Date.now()<startFlashUntil){
      els.bidBtn.disabled=true;
    } else if(!myPid){
      els.bidBtn.disabled=true;
      els.bidLabel.textContent='Užsiregistruok';
    } else {
      els.bidBtn.disabled = (lot.current_bidder===myNickname);
      els.bidLabel.textContent = (lot.current_bidder===myNickname) ? '👑 TU LYDERIAUJI' : 'KELTI KAINĄ +1 €';
    }
  }
  lastStatus = lot.status;
  if(lastLotId !== lot.id){ lastBidKey = null; }
  lastLotId = lot.id;

  if(!state.bids.length){els.feedList.innerHTML='<div class="feed-empty">Kol kas tylu.</div>';}
  else{
    var h='';
    state.bids.slice(0,12).forEach(function(b){
      var t=new Date(b.at*1000);
      h+='<div class="feed-row"><span>'+esc(b.name)+'</span><span class="feed-amt">'+fmt(b.amount)+' €</span><span class="feed-time">'+t.getHours()+':'+String(t.getMinutes()).padStart(2,'0')+':'+String(t.getSeconds()).padStart(2,'0')+'</span></div>';
    });
    els.feedList.innerHTML=h;
  }
  renderPast();
  renderQueueRail();
}
function buildTonightItems(){
  var items=[], seen={};
  var lot=state && state.lot;
  if(lot && (lot.status==='live' || (lot.status==='ended' && state.auction_locked))){
    items.push(Object.assign({}, lot, {_live:true}));
    seen[lot.id]=1;
  }
  ((state && state.queue)||[]).forEach(function(q){
    if(!q || seen[q.id]) return;
    items.push(Object.assign({}, q, {_live:false}));
    seen[q.id]=1;
  });
  return items;
}
function qrCardHtml(it, ord){
  var photo = it.photo_file ? '<img src="/photos/'+esc(it.photo_file)+'" alt="">' : '<span class="ph">nėra foto</span>';
  var price = it.starting_price!=null ? it.starting_price : it.current_price;
  var def = (it.defects||'').trim();
  var ordLabel = it._live ? 'Dabar' : ('#'+ord);
  var cls = 'qr-card'+(it._live?' now':'');
  return '<button type="button" class="'+cls+'" data-qr="'+ord+'" data-id="'+(it.id||'')+'">'+
    '<div class="qr-photo">'+photo+'</div>'+
    '<div class="qr-meta">'+
      '<span class="qr-ord">'+ordLabel+'</span>'+
      '<div class="qr-name">'+esc(it.title||'Prekė')+'</div>'+
      '<div class="qr-price">'+fmt(price)+'<small>€ start</small></div>'+
      (def?'<div class="qr-def">'+esc(def)+'</div>':'')+
    '</div></button>';
}
var qrItemsCache=[], qrSig='', qrPaused=false, qrOffset=0, qrRaf=0;
function renderQueueRail(){
  var rail=document.getElementById('queueRail');
  var track=document.getElementById('qrTrack');
  var countEl=document.getElementById('qrCount');
  if(!rail||!track) return;
  if(!isVilkasStageOn()){
    qrItemsCache=[];
    qrSig='cover';
    if(countEl) countEl.textContent='įžanga — prekės pasirodys kai įjungsime Vilką';
    rail.classList.add('qr-empty');
    track.innerHTML='<div style="padding:28px 16px;color:rgba(243,232,211,.4);font-size:13px;">Įžanga. Prekių eilė pasirodys, kai Mindaugas įjungs Vilką.</div>';
    qrOffset=0; track.style.transform='translateX(0)';
    return;
  }
  var items=buildTonightItems();
  qrItemsCache=items;
  var sig=items.map(function(x){return x.id+':'+(x.photo_file||'')+':'+(x.starting_price||'')+':'+(x.defects||'');}).join('|');
  if(countEl){
    countEl.textContent = items.length
      ? (items.length+' prekė'+(items.length===1?'':'s')+' · eilės tvarka')
      : 'kai bus prekių — čia slinks eilė';
  }
  rail.classList.toggle('qr-empty', !items.length);
  if(sig===qrSig) return;
  qrSig=sig;
  if(!items.length){
    track.innerHTML='<div style="padding:28px 16px;color:rgba(243,232,211,.4);font-size:13px;">Kol kas eilėje nieko — kai pridėsime, čia matysi eiliškumą.</div>';
    qrOffset=0; track.style.transform='translateX(0)';
    return;
  }
  var html='';
  items.forEach(function(it,i){ html+=qrCardHtml(it, i+1); });
  // dubliuoti sklandžiam auto-slinkimui
  if(items.length>=3){
    items.forEach(function(it,i){ html+=qrCardHtml(it, i+1); });
  }
  track.innerHTML=html;
  qrOffset=0; track.style.transform='translateX(0)';
  track.querySelectorAll('[data-qr]').forEach(function(btn){
    btn.onclick=function(){
      var ord=parseInt(btn.getAttribute('data-qr'),10);
      openQrModal(qrItemsCache[ord-1], ord);
    };
  });
}
function openQrModal(it, ord){
  if(!it) return;
  var m=document.getElementById('qrModal');
  if(!m) return;
  var img=document.getElementById('qrModalImg');
  if(it.photo_file){ img.src='/photos/'+it.photo_file; img.style.display='block'; }
  else { img.removeAttribute('src'); img.style.display='none'; }
  document.getElementById('qrModalOrd').textContent = it._live ? 'Dabar scenoje' : ('Eilėje #'+ord+' — ateis kai baigsis ankstesnė');
  document.getElementById('qrModalTitle').textContent = it.title||'Prekė';
  var sp = it.starting_price!=null ? it.starting_price : it.current_price;
  document.getElementById('qrModalPrice').textContent = 'Pradinė kaina: '+fmt(sp)+' €'+(it.shipping!=null?' · siuntimas '+fmt(it.shipping)+' €':'');
  function row(id, label, val){
    var el=document.getElementById(id);
    if(!el) return;
    if(val && String(val).trim()){ el.innerHTML='<b>'+label+':</b> '+esc(String(val).trim()); el.style.display='block'; }
    else { el.textContent=''; el.style.display='none'; }
  }
  row('qrModalCond','Būklė', it.condition);
  row('qrModalDef','Defektai', it.defects);
  row('qrModalPlus','Pliusai', it.pluses);
  row('qrModalInc','Komplektacija', it.included);
  row('qrModalDesc','Aprašymas', it.description);
  m.classList.add('open'); m.setAttribute('aria-hidden','false');
  qrPaused=true;
}
function speakQueueItem(it, ord){
  if(!it || !voiceOn) return;
  if(announceBusy || announceQueue.length) return;
  var title=speechTitle(it.title)||'ši prekė';
  var sp=it.starting_price!=null?it.starting_price:it.current_price;
  var def=(it.defects||'').trim();
  var line;
  if(it._live){
    line='Dabar scenoje — '+title+'! Pradinė kaina '+eurosWords(sp)+'.'+(def?' Defektas: '+def+'.':'')+' Kas kelia?';
  } else {
    line='Eilėje numeris '+ord+' — '+title+'. Startas nuo '+eurosWords(sp)+'.'+(def?' Sąžiningai: '+def+'.':'')+' Ateis, kai baigsis ankstesnė!';
  }
  queueAnnounce(capSentences(line), {pose:'present', bangs:0, gestures:['present','thumb','raise'],
    bubble:(it._live?'Dabar: ':'#'+ord+' ')+(it.title||'')});
}
function closeQrModal(){
  var m=document.getElementById('qrModal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden','true'); }
  qrPaused=false;
}
function qrStep(dir){
  var track=document.getElementById('qrTrack');
  var vp=document.getElementById('qrViewport');
  if(!track||!vp) return;
  var card=track.querySelector('.qr-card');
  var step=(card?card.offsetWidth:111)+8;
  qrPaused=true;
  qrOffset = Math.max(0, qrOffset + dir*step);
  var max = Math.max(0, track.scrollWidth/2 - vp.clientWidth);
  if(qrOffset>max) qrOffset=0;
  track.style.transition='transform .35s ease';
  track.style.transform='translateX(' + (-qrOffset) + 'px)';
  clearTimeout(qrStep._t);
  qrStep._t=setTimeout(function(){ qrPaused=false; track.style.transition='none'; }, 900);
}
function qrAutoTick(){
  var track=document.getElementById('qrTrack');
  var vp=document.getElementById('qrViewport');
  if(track && vp && !qrPaused && qrItemsCache.length>=2){
    qrOffset += 0.28;
    var half = track.scrollWidth/2;
    if(half>0 && qrOffset >= half) qrOffset -= half;
    track.style.transform='translateX(' + (-qrOffset) + 'px)';
  }
  qrRaf=requestAnimationFrame(qrAutoTick);
}
(function initQueueRail(){
  var prev=document.getElementById('qrPrev'), next=document.getElementById('qrNext');
  var vp=document.getElementById('qrViewport'), modal=document.getElementById('qrModal');
  var close=document.getElementById('qrModalClose');
  if(prev) prev.onclick=function(){ qrStep(-1); };
  if(next) next.onclick=function(){ qrStep(1); };
  if(vp){
    vp.addEventListener('mouseenter', function(){ qrPaused=true; });
    vp.addEventListener('mouseleave', function(){ if(!document.getElementById('qrModal').classList.contains('open')) qrPaused=false; });
    vp.addEventListener('touchstart', function(){ qrPaused=true; }, {passive:true});
  }
  if(close) close.onclick=closeQrModal;
  if(modal) modal.addEventListener('click', function(e){ if(e.target===modal) closeQrModal(); });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeQrModal(); });
  qrRaf=requestAnimationFrame(qrAutoTick);
})();
function renderPast(){
  // Ankstesni lotai viešai PASLĖPTI — ataskaita folderiuose sau
  if(els.pastBox) els.pastBox.style.display='none';
}

var announcedCount = null;
function tickCountdownOverlay(){
  var lot = state && state.lot;
  if(!lot || !lot.starts_at || lot.status==='ended'){ els.countdownOverlay.style.display='none'; announcedCount=null; return; }
  var remain = lot.starts_at*1000 - Date.now();
  if(remain<=0){
    if(announcedCount!==null && announcedCount>0){ startSound(); }
    els.countdownOverlay.style.display='none'; announcedCount=null; return;
  }
  els.countdownOverlay.style.display='flex';
  var n = Math.ceil(remain/1000);
  if(n !== announcedCount){
    announcedCount = n;
    if(n<=0){
      els.countdownNum.textContent='START';
      els.countdownNum.classList.add('start');
      startSound();
    } else {
      els.countdownNum.textContent = n;
      els.countdownNum.classList.remove('start');
      els.countdownNum.style.animation='none'; void els.countdownNum.offsetWidth; els.countdownNum.style.animation='';
      if(n<=10) tickSound();
    }
  }
}

function tick(){
  if(els.countdownOverlay) els.countdownOverlay.style.display='none';
  try{ tickButton(); }catch(e){}
  try{ watchAmbienceSmoke(); }catch(e){}
  var lot=state && state.lot;
  var ring=document.querySelector('.timer-ring');
  var inCd = lot && lot.starts_at && lot.starts_at*1000 > Date.now();
  /* Vienas laikrodis: kol Vilkas pristato — tik mygtuke 1:00; žiedas tik kai vyksta pirkimas */
  /* Be F9 lotai SUŠALDYTI — ends_at praeityje neturi sukti poll() kas 200 ms */
  if(!lot || lot.status==='ended' || inCd || (state && state.auction_locked) || !isVilkasStageOn()){
    if(els.timerNum) els.timerNum.textContent = (lot && lot.status==='ended') ? '0:00' : '1:00';
    if(els.timerCircle) els.timerCircle.style.strokeDashoffset=0;
    if(ring) ring.style.opacity = inCd ? '0.35' : '1';
    return;
  }
  if(ring) ring.style.opacity='1';
  if(!lot.ends_at){ if(els.timerNum) els.timerNum.textContent='1:00'; return; }
  var remain=lot.ends_at*1000-Date.now();
  if(remain<=0){els.timerNum.textContent='0:00';pollSoon();return;}
  els.timerNum.textContent=timeStr(remain);
  var frac=remain/60000, C=2*Math.PI*32;
  els.timerCircle.style.strokeDashoffset=C*(1-Math.min(1,frac));
  els.timerCircle.style.stroke=frac<0.2?'#ff4d4d':'#ff7a33';
}
var pollBusy=false, pollLastAt=0;
function poll(){
  pollLastAt=Date.now();
  fetch('/api/state').then(function(r){return r.json();}).then(function(d){state=d;render();})
    .catch(function(){});
}
function pollSoon(){
  if(pollBusy || Date.now()-pollLastAt<1000) return;
  pollBusy=true; pollLastAt=Date.now();
  fetch('/api/state').then(function(r){return r.json();}).then(function(d){state=d;render();})
    .catch(function(){})
    .then(function(){ pollBusy=false; });
}
var serverEventSeen={}, serverEventOrder=[], lastServerEventId=0, eventSocket=null, eventSocketOpen=false;
function rememberServerEvent(id){
  id=Number(id)||0;
  if(!id || serverEventSeen[id]) return false;
  serverEventSeen[id]=1; serverEventOrder.push(id);
  while(serverEventOrder.length>600){ delete serverEventSeen[serverEventOrder.shift()]; }
  lastServerEventId=Math.max(lastServerEventId,id);
  return true;
}
function announceQueueHasTag(tag){
  for(var i=0;i<announceQueue.length;i++){ if(announceQueue[i] && announceQueue[i].tag===tag) return true; }
  return !!(announceBusy && announceCurrentJob && announceCurrentJob.tag===tag);
}
function clearPhoneJobsFromQueue(){
  try{
    announceQueue=(announceQueue||[]).filter(function(j){ return !(j && j.tag==='phone'); });
  }catch(e){}
}
function serverPhone(text, manual){
  /* F11 PRIVALOMA eiga:
     1) STOP visi kelimai/pokalbiai
     2) skambutis skamba
     3) „Atsiprašau žmonės, einu pakalbėti“
     4) Vilkas IŠNYKSTA ~1 min
     5) grįžta: „Viršininkas skambino… ko neperka žmonės?“
     6) jei kas kėlė — catchup vardai */
  text=String(text||'').trim();
  if(!manual){
    if(phoneCallActive || phoneSessionActive || announceQueueHasTag('phone')) return;
    if(!text) text=phoneExcuseLine();
    beginPhoneSession();
    queueAnnounce('',{tag:'phone',pose:'glasses',bangs:0,playMs:2200,bubble:'📞 Skambutis',
      gestures:['glasses'],onSpeak:function(){ setPhoneCallActive(true); if(isAudioMaster()) phoneRingSound(); },
      onDone:function(){ try{if(phoneRingAudio){phoneRingAudio.pause();phoneRingAudio=null;}}catch(e){} }});
    queueAnnounce(text,{tag:'phone',pose:'glasses',bangs:0,gestures:['glasses','wink','raise'],bubble:'📞 Alio…',
      onDone:function(){ try{ endPhoneSessionAndCatchup(); }catch(e){} }});
    return;
  }
  /* F11 manual — VISADA pertraukiam bid/nudge/joke (net lot_intro soft); sold paliekam protected per interrupt. */
  try{ interruptAllSpeech(); }catch(e){}
  beginPhoneSession();
  try{ if(isAudioMaster()) phoneRingSound(); }catch(e2){}
  try{ wolfPopShow('glasses'); }catch(e3){}
  try{ setBubble('📞 Skambutis', ''); }catch(e4){}
  clearTimeout(phoneSpeechTimer);
  phoneSpeechTimer=setTimeout(function(){
    phoneSpeechTimer=null;
    try{ if(phoneRingAudio){ phoneRingAudio.pause(); phoneRingAudio.currentTime=0; phoneRingAudio=null; } }catch(e5){}
    try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e6){}
    /* Atlaisvinam eilę — phoneCallActive kitaip ryja „Atsiprašau“ (skamba, bet nekalba). */
    setPhoneCallActive(false);
    try{ if(typeof claimAudioMaster==='function') claimAudioMaster(true); }catch(eM){}
    clearPhoneJobsFromQueue();
    var excuse=phoneExcuseLine();
    queueAnnounce(excuse,{tag:'phone',priority:true,pose:'glasses',bangs:0,gestures:['glasses','wink'],bubble:'📞 Atsiprašau…',
      onDone:function(){
        queueAnnounce(text,{tag:'phone',priority:true,pose:'glasses',bangs:0,gestures:['glasses','raise'],bubble:'📞 Alio…',
          onDone:function(){
            try{ hideVilkasPhoneAway(); }catch(eH){}
            try{ clearTimeout(phoneAwayTimer); }catch(eT){}
            phoneAwayTimer=setTimeout(function(){
              phoneAwayTimer=null;
              try{ showVilkasAfterPhone(); }catch(eS){}
              try{ endPhoneSessionAndCatchup(); }catch(eE){}
            }, 60000);
          }});
      }});
  }, 2200);
}

var heardWelcome=false; var heardLotIntro={};
var pendingStageEvents=[];
function handleServerEvent(ev){
  if(!ev) return;
  if(!isVilkasStageOn()){
    if(ev.event_type==='lot_intro' || ev.event_type==='welcome' || ev.event_type==='start'){
      pendingStageEvents.push(ev);
    }
    return;
  }
  if(!rememberServerEvent(ev.event_id)) return;
  var now=Date.now(), age=now-(Number(ev.created_at)||0)*1000;
  var p=ev.payload||{}, lot=state&&state.lot;
  var phoneManual=!!(ev.event_type==='phone' && p.manual);
  var maxAge={bid:15000,nudge:18000,phone:18000,joke:22000,guitar:22000,start:18000,sold:45000,intermission:45000,welcome:25000,lot_intro:40000};
  if(phoneManual) maxAge.phone=60000;
  if(ev.expires_at && Number(ev.expires_at)*1000<=now) return;
  if(maxAge[ev.event_type] && age>maxAge[ev.event_type]) return;
  /* Kito loto intro/start NEGALI dingti malonės metu (state dar senas ended).
     phone (ypač F11 manual) — NEMESTI dėl lot_id neatitikimo. */
  if(p.lot_id && lot && Number(p.lot_id)!==Number(lot.id)){
    if(ev.event_type!=='lot_intro' && ev.event_type!=='start' && ev.event_type!=='welcome' && ev.event_type!=='phone') return;
  }
  var text=String(p.text||'').trim();
  /* Perduoda mokyklos parinktą intonaciją į kalbą. */
  var femBid=false;
  try{ femBid=(ev.event_type==='bid') && !!isFemaleName(p.name||''); }catch(eF){}
  var itoId=String(p.intonacija_id||'');
  var itoSexy=femBid || p.female_name===true || String(p.intonacija||'')==='seksuali' || itoId==='int-sexy';
  var itoSpeed=(p.speed && Number(p.speed)>0)?Number(p.speed):(itoSexy?0.93:0);
  /* Skambučio metu — jokių soft komentarų (nudge/joke/gitara/dainavimas). */
  if(isPhoneBusy() && (ev.event_type==='nudge'||ev.event_type==='joke'||ev.event_type==='guitar'||ev.event_type==='sing'||ev.event_type==='lot_intro'||ev.event_type==='welcome'||ev.event_type==='start')) return;
  if(ev.event_type==='bid'){
    if(coffeeActive) endCoffee();
    if(isPhoneBusy()){
      holdBidDuringPhone(p.name||'Dalyvis', Number(p.amount)||0);
      return;
    }
    /* Serverio tekstas (mokykla bid frazės) — jei yra; kitaip gyvas bidLine */
    if(text && text.length>8){
      try{ hitGong(); }catch(eG){}
      try{ cheerBurst(); }catch(eC){}
      var bubbleB='🔔 '+(p.name||'Dalyvis')+' → '+Math.round(Number(p.amount)||0)+' €';
      try{ setBubble(bubbleB, text); }catch(eB){}
      var nowB=Date.now();
      if(nowB-lastBidSpeechAt>=9000){
        lastBidSpeechAt=nowB;
        var optsB={tag:'bid', priority:true, pose:'bang', bangs:0, fast:!itoSexy, fx:'cheer',
          gestures:['bang',bidPose(p.name||''),'thumb'], gestureMs:350, bubble:bubbleB};
        if(itoSpeed) optsB.speed=itoSpeed;
        if(announceBusy || announceQueueHasProtected() || !announceQueueSoftOnly()) queueAnnounce(text, optsB);
        else { interruptAllSpeech(); queueAnnounce(text, optsB); }
      }
    } else {
      speakBidNow(p.name||'Dalyvis',Number(p.amount)||0);
    }
  } else if(ev.event_type==='sold'){
    interruptAllSpeech();
    if(p.winner) speakSold(p.winner,Number(p.price)||0,p.lot_id);
    else if(text) queueAnnounce(text,{tag:'sold',pose:'bow',bangsBefore:1,gong:true,bangs:0,after:'bow',bubble:'Lotas baigtas'});
  } else if(ev.event_type==='phone'){
    if(text) serverPhone(text, phoneManual);
  } else if(ev.event_type==='joke'){
    if(text) queueAnnounce(text,{tag:'joke',pose:'wink',bangs:0,fx:'laugh',gestures:['wink','glasses','raise'],bubble:'😄 Vilko bajeriukas'});
  } else if(ev.event_type==='guitar'){
    return; /* Ignoruojami ir seni gitaros įvykiai iš eilės / DB. */
  } else if(ev.event_type==='sing'){
    /* Trumpas dainavimas su muzika — duck švelnus, bitas lieka */
    if(text){
      try{ if(practiceModeOn && typeof makeRadioAudibleNow==='function') makeRadioAudibleNow(); }catch(eS){}
      queueAnnounce(text,{tag:'sing',pose:'raise',bangs:0,fx:'notes',gestures:['raise','welcome','clap'],bubble:'🎤 Vilkas dainuoja'+(p.daina?(': '+p.daina):''),
        onSpeak:function(){ try{ if(typeof makeRadioAudibleNow==='function') makeRadioAudibleNow(); }catch(e2){} }});
    }
  } else if(ev.event_type==='intermission'){
    if(p.skip_coffee){
      if(text) queueAnnounce(text,{tag:'intermission',pose:'present',bangs:0,gestures:['present','raise'],bubble:'➡️ Kitas lotas'});
      return;
    }
    if(text) queueAnnounce(text,{tag:'intermission',pose:'coffee',bangs:0,gestures:['coffee'],bubble:'☕ Pertrauka',onDone:function(){
      startIntermissionCoffee(p.lot_id);
    }});
    if((Number(p.lot_id)||0)%3===0) queueAnnounce(
      'Jūs man paskambinkite dėl prekių realizavimo. Aš laukiu jūsų skambučio.',
      {tag:'intermission',pose:'glasses',bangs:0,gestures:['glasses','welcome','raise'],bubble:'📞 +37066331913',
       onSpeak:function(){ photographedWolf('Prekių realizavimas', 'glasses'); }}
    );
  } else if(ev.event_type==='start'){
    if(text) queueAnnounce(text,{tag:'start',priority:true,pose:'welcome',bangsBefore:1,gong:true,bangs:0,gestures:CLAP.concat(['raise']),bubble:'🔨 PRADEDAME!'});
  } else if(ev.event_type==='lot_intro'){
    try{ if(coffeeActive) endCoffee(); }catch(e){}
    try{
      /* Soft intermission/kava — išmesk, kad pristatymas nelauktų */
      announceQueue=announceQueue.filter(function(j){
        return j && j.tag!=='intermission' && j.tag!=='joke' && j.tag!=='phone' && j.tag!=='nudge' && j.tag!=='guitar' && j.tag!=='sing';
      });
      if(announceBusy && announceCurrentJob && (announceCurrentJob.tag==='intermission'||announceCurrentJob.tag==='joke'||announceCurrentJob.tag==='phone'||announceCurrentJob.tag==='nudge'||announceCurrentJob.tag==='guitar'||announceCurrentJob.tag==='sing')){
        interruptAllSpeech();
      }
    }catch(e){}
    var lid=String(p.lot_id||'')+'@'+String(p.starts_at||'');
    if(heardLotIntro[lid]) return;
    heardLotIntro[lid]=1;
    try{ wolfPopShow('present'); }catch(e){}
    setTimeout(function(){ welcomeWolfForLot(p); },1000);
    if(text) queueAnnounce(text,{tag:'lot_intro',priority:true,pose:'present',bangs:1,gestures:['present','welcome','thumb'],bubble:'🎤 Lotas #'+(p.lot_number||'')+': '+(p.title||''),fast:false,speed:1.00});
  } else if(ev.event_type==='welcome'){
    if(heardWelcome) return;
    heardWelcome=true;
    var coffeeMs=Math.max(60000, (Number(p.coffee_s)||120)*1000);
    if(text) queueAnnounce(text,{tag:'welcome',pose:'welcome',bangs:0,gestures:['welcome','present','raise'],bubble:'Penktadienio aukcionas',
      onDone:function(){ try{ startOpeningCoffee(coffeeMs); }catch(e){} }});
  } else if(ev.event_type==='nudge' && text){
    queueAnnounce(text,{tag:'nudge',pose:'raise',bangs:0,gestures:['raise','welcome','thumb'],bubble:'Kas kitas?'});
  }
}
function applySocketMessage(msg){
  if(!msg) return;
  if(msg.kind==='state' && msg.state){ state=msg.state; render(); }
  else if(msg.kind==='event') handleServerEvent(msg.event);
}
function connectEvents(){
  if(eventSocket && (eventSocket.readyState===0 || eventSocket.readyState===1)) return;
  var proto=location.protocol==='https:'?'wss:':'ws:';
  eventSocket=new WebSocket(proto+'//'+location.host+'/ws?last_event_id='+lastServerEventId);
  eventSocket.onopen=function(){ eventSocketOpen=true; };
  eventSocket.onmessage=function(e){ try{ applySocketMessage(JSON.parse(e.data)); }catch(err){ reportClientError(err.message,'websocket',0,0,err.stack); } };
  eventSocket.onclose=function(){ eventSocketOpen=false; setTimeout(connectEvents,1800); };
  eventSocket.onerror=function(){ eventSocketOpen=false; };
}
function pollEventsFallback(){
  if(eventSocketOpen) return;
  fetch('/api/events?last_event_id='+lastServerEventId)
    .then(function(r){return r.json();})
    .then(function(d){(d.events||[]).forEach(handleServerEvent);})
    .catch(function(){});
}

/* === VILKO_MOKYKLA_CLIENT_START (Fable 2026-10-08) === */
var vilkoBrain=null, vilkoLastBidAt=0;
function vilkoParams(){ try{ return (vilkoBrain&&vilkoBrain.judesiai&&vilkoBrain.judesiai.parametrai)||{}; }catch(e){ return {}; } }
function vilkoApplyMotion(p){
  try{
    var r=document.documentElement.style;
    if(p.bob_px!=null) r.setProperty('--wolf-bob-px',p.bob_px+'px');
    if(p.sway_deg!=null) r.setProperty('--wolf-sway-deg',p.sway_deg+'deg');
    if(p.talk_s!=null) r.setProperty('--wolf-talk-s',p.talk_s+'s');
    if(p.walk_ms!=null) r.setProperty('--wolf-walk-ms',Math.round(p.walk_ms)+'ms');
    if(p.raise_px!=null) r.setProperty('--wolf-raise-px',p.raise_px+'px');
    if(p.fade_ms!=null) r.setProperty('--wolf-fade-ms',Math.round(p.fade_ms)+'ms');
    if(p.idle_s!=null) r.setProperty('--wolf-idle-s',p.idle_s+'s');
    if(p.ease) r.setProperty('--wolf-ease',p.ease);
  }catch(e){}
}
function vilkoFetchBrain(){
  fetch('/api/vilkas/brain',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
    if(d&&d.ok){ vilkoBrain=d; vilkoApplyMotion(vilkoParams()); }
  }).catch(function(){});
}
function vilkoFeedback(kind,payload){
  try{
    var body=JSON.stringify({kind:kind,payload:payload||{}});
    if(navigator.sendBeacon){ navigator.sendBeacon('/api/vilkas/feedback', new Blob([body],{type:'application/json'})); return; }
    fetch('/api/vilkas/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:body,keepalive:true}).catch(function(){});
  }catch(e){}
}
function vilkoSeq(tag){
  try{
    var arr=vilkoBrain&&vilkoBrain.judesiai&&vilkoBrain.judesiai.sekos&&vilkoBrain.judesiai.sekos[tag];
    if(!arr||!arr.length) return null;
    function beta(a,b){ /* Thompson: paprasta Beta aproksimacija per gamma (Marsaglia) */
      function g(k){ if(k<1){ return g(k+1)*Math.pow(Math.random(),1/k); } var d=k-1/3,c=1/Math.sqrt(9*d); for(;;){ var x,v; do{ x=(Math.random()*2-1)+(Math.random()*2-1)+(Math.random()*2-1); v=1+c*x; }while(v<=0); v=v*v*v; var u=Math.random(); if(u<1-0.0331*x*x*x*x) return d*v; if(Math.log(u)<0.5*x*x+d*(1-v+Math.log(v))) return d*v; } }
      var x=g(a),y=g(b); return x/(x+y);
    }
    var best=null,bv=-1;
    for(var i=0;i<arr.length;i++){ var v=beta(Math.max(0.05,+arr[i].a||1),Math.max(0.05,+arr[i].b||1)); if(v>bv){bv=v;best=arr[i];} }
    return best?{id:best.id,seq:(best.seka||[]).slice()}:null;
  }catch(e){ return null; }
}
/* Jank / pertraukimų matavimas gesto metu (tik audio-master — vienas matuotojas) */
var vilkoJank={on:false,jank:0,last:0,start:0,seqId:null,tag:null,bids:0,raf:null};
function vilkoJankStart(seqId,tag){
  if(typeof isAudioMaster==='function' && !isAudioMaster()) return;
  vilkoJank={on:true,jank:0,last:performance.now(),start:performance.now(),seqId:seqId,tag:tag,bids:0,raf:null};
  function loop(t){ if(!vilkoJank.on) return; var dt=t-vilkoJank.last; vilkoJank.last=t; if(dt>50) vilkoJank.jank+=dt-50; vilkoJank.raf=requestAnimationFrame(loop); }
  vilkoJank.raf=requestAnimationFrame(loop);
}
function vilkoJankStop(interrupted){
  if(!vilkoJank.on) return;
  var j=vilkoJank; vilkoJank.on=false; if(j.raf) cancelAnimationFrame(j.raf);
  var dur=performance.now()-j.start;
  vilkoFeedback('motion',{jank_ms:Math.round(j.jank),dur_ms:Math.round(dur),interrupted:!!interrupted,bid_during:j.bids,tag:j.tag,seq_id:j.seqId});
  if(j.seqId){
    var t0=Date.now();
    setTimeout(function(){ vilkoFeedback('gesture',{seq_id:j.seqId,tag:j.tag,bid_within:(vilkoLastBidAt>=t0-dur)?1:0,interrupted:!!interrupted}); }, 20000);
  }
}
/* Grakštūs judesiai */
function wolfWalkIn(){
  try{
    var pop=document.getElementById('wolfPop'); if(!pop) return;
    pop.classList.remove('walk-in'); void pop.offsetWidth; pop.classList.add('walk-in');
    var ms=+(vilkoParams().walk_ms||900);
    setTimeout(function(){ pop.classList.remove('walk-in'); }, ms+40);
  }catch(e){}
}
function wolfRaiseHand(){
  try{
    var pop=document.getElementById('wolfPop'); if(!pop) return;
    pop.classList.remove('raise-hand'); void pop.offsetWidth; pop.classList.add('raise-hand');
    try{ setPose('raise'); }catch(e){}
    setTimeout(function(){ pop.classList.remove('raise-hand'); }, 760);
  }catch(e){}
}
/* startGestures supranta 'walk' / 'raisehand'; tempas iš smegenų */
(function(){
  var _orig=startGestures;
  startGestures=function(list, ms){
    var l=[];
    (list||[]).forEach(function(g){
      if(g==='walk'){ wolfWalkIn(); return; }
      if(g==='raisehand'){ wolfRaiseHand(); l.push('raise'); return; }
      l.push(g);
    });
    return _orig(l, ms || +(vilkoParams().gesture_ms||0) || undefined);
  };
})();
/* queueAnnounce: išmokta gestų seka pagal tag + matavimas */
(function(){
  var _orig=queueAnnounce;
  queueAnnounce=function(text, opts){
    try{
      if(opts && typeof opts==='object' && opts.tag && !opts._vk){
        var tag=opts.tag==='lot_intro'?'lot_intro':opts.tag;
        var s=vilkoSeq(tag);
        if(s && s.seq.length>=2 && !opts.playMs){
          opts._vk=s.id;
          opts.gestures=s.seq;
          if(!opts.gestureMs) opts.gestureMs=+(vilkoParams().gesture_ms||0)||undefined;
          var oS=opts.onSpeak; opts.onSpeak=function(){ vilkoJankStart(s.id,tag); if(oS) return oS.apply(this,arguments); };
          var oD=opts.onDone; opts.onDone=function(){ vilkoJankStop(false); if(oD) return oD.apply(this,arguments); };
        }
      }
    }catch(e){}
    return _orig(text, opts);
  };
})();
(function(){
  var _oI=interruptAllSpeech;
  interruptAllSpeech=function(){ try{ if(vilkoJank.on) vilkoJankStop(true); }catch(e){} return _oI.apply(this,arguments); };
  var _oB=speakBidNow;
  speakBidNow=function(){ vilkoLastBidAt=Date.now(); try{ if(vilkoJank.on) vilkoJank.bids++; }catch(e){} return _oB.apply(this,arguments); };
})();
/* Soft-sway, kai Vilkas scenoje tyli (grakštus kvėpavimas, ne trypčiojimas) */
setInterval(function(){
  try{
    var pop=document.getElementById('wolfPop'); if(!pop) return;
    var on=(typeof isVilkasStageOn==='function' && isVilkasStageOn()) && pop.classList.contains('show') && !announceBusy && !hostAudio && !phoneCallActive;
    pop.classList.toggle('soft-sway', !!on);
  }catch(e){}
}, 700);
vilkoFetchBrain(); setInterval(vilkoFetchBrain, 300000);
/* === VILKO_MOKYKLA_CLIENT_END === */

ensureBuyerSession(function(){
  poll();
  connectEvents();
  setInterval(poll, 3000);
  setInterval(pollEventsFallback, 2500);
  setInterval(function(){
    fetch('/api/desk_song').then(function(r){return r.json();}).then(function(d){
      try{ applyDeskSong({desk_song: d.song || null}); }catch(e){}
    }).catch(function(){});
  }, 700);
});
setInterval(tick, 200);
</script>
</body></html>"""

ADMIN_HTML = r"""<!doctype html><html lang="lt"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Penktadienio aukcionas · pardavėjas</title>
<link rel="icon" href="data:,">
<style>
:root{--bg:#14100c;--surface:#1f1811;--surface-2:#2a2018;--surface-3:#362a1e;--border:#40331f;--text:#f3ead9;--text-dim:#b9a88f;--text-faint:#7d6f5b;--accent:#ff7a33;--accent-2:#ffb347;--gold:#e3b23c;--good:#4caf7d;--bad:#e05a5a;}
*{box-sizing:border-box;}
body{margin:0;font-family:Archivo,Arial,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.wrap{max-width:920px;margin:0 auto;padding:28px 16px 60px;}
h1{font-size:20px;margin:0 0 4px;}
.sub{color:var(--text-faint);font-size:13px;margin:0 0 24px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:18px;}
.card h2{font-size:14px;margin:0 0 14px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.06em;font-family:monospace;}
.reg-table{width:100%;border-collapse:collapse;font-size:12.5px}
.reg-table th,.reg-table td{border-bottom:1px solid var(--border);padding:7px 6px;text-align:left;vertical-align:top}
.reg-table th{color:var(--text-faint);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.reg-table tr:hover td{background:var(--surface-2)}
.dom-pill{display:inline-block;margin:0 6px 6px 0;padding:4px 8px;border-radius:999px;background:var(--surface-2);border:1px solid var(--border);font-size:12px;color:var(--text-dim)}
.dom-pill b{color:var(--good)}
label{display:block;font-size:12px;color:var(--text-faint);margin:10px 0 5px;}
label:first-of-type{margin-top:0;}
input[type=text],input[type=number],input[type=password],textarea{width:100%;background:var(--surface-2);border:1px solid var(--border);color:var(--text);padding:10px 12px;border-radius:9px;font-family:inherit;font-size:14px;outline:none;}
textarea{resize:vertical;}
input[type=file]{width:100%;color:var(--text-dim);font-size:13px;}
button{font-family:inherit;cursor:pointer;border:none;border-radius:9px;font-weight:700;}
.btn-main{width:100%;background:linear-gradient(180deg,var(--accent-2),var(--accent));color:#1a1006;padding:13px;font-size:15px;margin-top:14px;}
.btn-main:disabled{opacity:.5;cursor:not-allowed;}
.btn-danger{background:var(--bad);color:#fff;padding:9px 14px;font-size:12.5px;}
.btn-ghost{background:var(--surface-3);color:var(--text);padding:7px 10px;font-size:13px;}
.msg{margin-top:10px;font-size:13px;min-height:16px;}
.msg.ok{color:var(--good);}
.msg.err{color:var(--bad);}
.preview{margin-top:10px;display:none;}
.preview img{width:100%;max-height:180px;object-fit:cover;border-radius:10px;border:1px solid var(--border);}
.live-row{display:flex;gap:12px;align-items:center;}
.live-row img{width:64px;height:64px;object-fit:cover;border-radius:8px;flex:none;background:var(--surface-2);}
.live-info{flex:1;min-width:0;}
.live-title{font-weight:700;font-size:14.5px;margin-bottom:2px;}
.live-meta{font-size:12.5px;color:var(--text-dim);}
.empty-note{color:var(--text-faint);font-size:13px;}
.q-row{display:flex;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border);}
.q-row:last-child{border-bottom:none;}
.q-row img{width:44px;height:44px;object-fit:cover;border-radius:7px;flex:none;background:var(--surface-2);}
.q-info{flex:1;min-width:0;font-size:13px;}
.q-info b{display:block;font-size:13.5px;}
.q-actions{display:flex;gap:5px;flex:none;}
.q-actions button{width:26px;height:26px;padding:0;background:var(--surface-3);color:var(--text-dim);font-size:12px;border-radius:6px;}
.q-actions button.del{color:var(--bad);}
.past-row{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px solid var(--border);font-size:12.5px;color:var(--text-dim);}
.past-row:last-child{border-bottom:none;}
.past-row b{color:var(--good);font-weight:700;}
#loginCard{max-width:340px;margin:80px auto 0;}
.top-link{display:block;text-align:center;margin-top:20px;font-size:12.5px;color:var(--text-faint);}
.top-link a{color:var(--text-faint);}
.logout{float:right;font-size:12px;color:var(--text-faint);cursor:pointer;text-decoration:underline;}
</style></head><body>
<div class="wrap">

<div class="card" id="loginCard">
  <h2>Prisijungimas</h2>
  <label>Administratoriaus slaptažodis</label>
  <input type="password" id="loginPass">
  <button class="btn-main" id="loginBtn">Prisijungti</button>
  <div class="msg err" id="loginMsg"></div>
</div>

<div id="dash" style="display:none;">
  <h1>Penktadienio aukcionas <span class="logout" id="logoutBtn">atsijungti</span></h1>
  <p class="sub">Pardavėjo skydelis — dabartinis lotas, eilė ir istorija.</p>

  <div class="card">
    <h2>Dabar vyksta</h2>
    <div id="liveBox"><div class="empty-note">Šiuo metu nėra gyvo loto.</div></div>
  </div>

  <div class="card">
    <h2>Registracijos (<span id="regCount">0</span>)</h2>
    <p class="sub" style="margin-bottom:10px;">Visi žmonės, kurie užpildė formą — vardas, slapyvardis, el. paštas, telefonas, domenas, mokėjimo būdas. Failai serveryje: <code>admin_registracijos/</code> · Desktop: <code>ADMINISTRACIJA_REGISTRACIJOS</code></p>
    <div id="domBox" style="margin-bottom:12px"></div>
    <div id="regBox"><div class="empty-note">Kol kas nėra registracijų.</div></div>
  </div>

  <div class="card">
    <h2>Pridėti naują prekę</h2>
    <p class="sub" style="margin-bottom:10px;">Jei lotas dabar nevyksta — prekė paskelbiama iškart. Jei vyksta — automatiškai atsiduria eilėje ir prasidės, kai baigsis dabartinis.</p>
    <form id="addForm">
      <label>Pavadinimas</label>
      <input type="text" name="title" required maxlength="80">
      <label>Aprašymas</label>
      <textarea name="description" rows="4" placeholder="Būklė, komplektacija, defektai ir t.t."></textarea>
      <label>Starto kaina (€)</label>
      <input type="number" name="price" step="0.5" value="1" min="0">
      <label>Siuntimas (€)</label>
      <input type="number" name="shipping" step="0.5" value="4" min="0">
      <label>Pliusai (per kabliataškį ;)</label>
      <input type="text" name="pluses" placeholder="baterija 90%; 128GB; greitas">
      <label>Defektai (tuščia = nėra)</label>
      <input type="text" name="defects" placeholder="įbrėžimas ant ekrano kampo">
      <label>Komplektacija</label>
      <input type="text" name="included" placeholder="kroviklis; dėklas">
      <label>Būklė (nauja / kaip_nauja / gera / naudota)</label>
      <input type="text" name="condition" placeholder="gera">
      <label>Nuotrauka</label>
      <input type="file" name="photo" accept="image/*" id="photoInput">
      <div class="preview" id="previewBox"><img id="previewImg"></div>
      <button type="submit" class="btn-main" id="addBtn">Pridėti prekę</button>
    </form>
    <div class="msg" id="addMsg"></div>
  </div>

  <div class="card">
    <h2>Eilė (<span id="queueCount">0</span>)</h2>
    <div id="queueBox"><div class="empty-note">Eilėje nieko nėra.</div></div>
  </div>

  <div class="card">
    <h2>Istorija</h2>
    <div id="pastBox"><div class="empty-note">Kol kas nieko neparduota.</div></div>
  </div>

  <div class="card">
    <h2>Švarus startas</h2>
    <p class="sub" style="margin-bottom:10px;">Ištrina VISĄ istoriją, eilę ir dalyvių sąrašą — naudinga tik prieš pradedant iš naujo (pvz. po testavimo). Aktyvių prekių tai neliečia.</p>
    <button class="btn-danger" id="resetBtn" style="width:100%;padding:11px;">Išvalyti visus testinius duomenis</button>
    <div class="msg" id="resetMsg"></div>
  </div>

  <div class="top-link"><a href="/">← į aukciono puslapį</a></div>
</div>

</div>
<script>
var pass = localStorage.getItem('admin_pass') || '';
var els = {};
['loginCard','loginPass','loginBtn','loginMsg','dash','liveBox','addForm','addMsg','addBtn','photoInput','previewBox','previewImg','queueBox','queueCount','pastBox','logoutBtn','resetBtn','resetMsg','regCount','regBox','domBox'].forEach(function(id){els[id]=document.getElementById(id);});

function fmt(n){return (n||0).toLocaleString('lt-LT',{minimumFractionDigits:2,maximumFractionDigits:2});}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}

function showDash(){ els.loginCard.style.display='none'; els.dash.style.display='block'; refresh(); }
function showLogin(msg){ els.loginCard.style.display='block'; els.dash.style.display='none'; if(msg) els.loginMsg.textContent=msg; }

els.loginBtn.onclick=function(){
  var p = els.loginPass.value;
  if(!p){ els.loginMsg.textContent='Įvesk slaptažodį.'; return; }
  fetch('/api/admin/dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})})
    .then(function(r){ if(r.status===403){ throw new Error('bad'); } return r.json(); })
    .then(function(){ pass=p; localStorage.setItem('admin_pass',p); els.loginMsg.textContent=''; showDash(); })
    .catch(function(){ els.loginMsg.textContent='Neteisingas slaptažodis.'; });
};
els.loginPass.addEventListener('keydown', function(e){ if(e.key==='Enter') els.loginBtn.click(); });
els.logoutBtn.onclick=function(){ localStorage.removeItem('admin_pass'); pass=''; showLogin(''); };

els.resetBtn.onclick=function(){
  if(!confirm('Tikrai ištrinti VISĄ istoriją, eilę ir dalyvių sąrašą? Šio veiksmo atšaukti negalima.')) return;
  if(!confirm('Paskutinis patvirtinimas — viskas bus ištrinta negrįžtamai. Tęsti?')) return;
  fetch('/api/admin/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass})})
    .then(function(r){return r.json();}).then(function(){
      els.resetMsg.className='msg ok'; els.resetMsg.textContent='Išvalyta.'; refresh();
    });
};

els.photoInput.onchange=function(){
  var f = els.photoInput.files[0];
  if(!f){ els.previewBox.style.display='none'; return; }
  els.previewImg.src = URL.createObjectURL(f);
  els.previewBox.style.display='block';
};

els.addForm.onsubmit=function(e){
  e.preventDefault();
  var fd = new FormData(els.addForm);
  fd.append('password', pass);
  els.addBtn.disabled = true; els.addBtn.textContent = 'Skelbiama...';
  fetch('/api/admin/add',{method:'POST',body:fd})
    .then(function(r){ return r.json().then(function(d){ return {ok:r.ok, d:d}; }); })
    .then(function(res){
      els.addBtn.disabled=false; els.addBtn.textContent='Pridėti prekę';
      if(res.ok){
        els.addMsg.className='msg ok';
        els.addMsg.textContent = res.d.status==='live' ? ('Lotas #'+res.d.lot_number+' paskelbtas ir jau prasideda!') : ('Lotas #'+res.d.lot_number+' pridėtas į eilę.');
        els.addForm.reset(); els.previewBox.style.display='none';
        refresh();
      } else {
        els.addMsg.className='msg err';
        els.addMsg.textContent = 'Klaida: '+(res.d.detail||'nežinoma');
      }
    })
    .catch(function(){ els.addBtn.disabled=false; els.addBtn.textContent='Pridėti prekę'; els.addMsg.className='msg err'; els.addMsg.textContent='Nepavyko susisiekti su serveriu.'; });
};

function queueAction(url, id, extra){
  var body = Object.assign({password:pass, id:id}, extra||{});
  fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(refresh);
}

function renderDash(d){
  var lot = d.lot;
  var wp = d.winner_pay;
  if(!lot){
    els.liveBox.innerHTML = '<div class="empty-note">Šiuo metu nėra gyvo loto.</div>';
  } else {
    var img = lot.photo_file ? '<img src="/photos/'+lot.photo_file+'">' : '<img>';
    var starting = lot.starts_at && lot.starts_at*1000>Date.now();
    var statusTxt = starting ? 'pasiruošęs, tuoj prasidės' : ('kaina '+fmt(lot.current_price)+' €'+(lot.current_bidder?(' · siūlo '+esc(lot.current_bidder)):' · dar be pasiūlymų'));
    var payBlock = '';
    if(lot.status==='ended' && wp){
      var subj = encodeURIComponent('Mokėjimas: lotas #'+wp.lot_number+' '+wp.lot_title);
      var body = encodeURIComponent(
        'Sveiki, '+wp.winner_nickname+'!\n\n'+
        'Laimėjote lotą #'+wp.lot_number+' „'+wp.lot_title+'“ už '+wp.amount.toFixed(2)+' €'+
        (wp.shipping?(' + siuntimas '+wp.shipping.toFixed(2)+' €'):'')+
        ' = '+wp.total.toFixed(2)+' €.\n\n'+
        'Mokėkite per '+wp.pay_label+' į: '+wp.pay_email+'\n'+
        wp.pay_hint+'\n\n'+
        'Paskirtyje nurodykite savo slapyvardį ir loto pavadinimą.\n'+
        'Sumokėję atsakykite į šį laišką dėl siuntimo.\n\nVilkas / Penktadienio aukcionas'
      );
      payBlock =
        '<div style="margin-top:10px;padding:10px;border:1px solid #2f5c44;border-radius:10px;background:#132018;font-size:13px;line-height:1.45;">'+
        '<b>Laimėtojo mokėjimas (privatu)</b><br>'+
        'Kontaktas: <b>'+esc(wp.winner_contact)+'</b><br>'+
        'Būdas: <b>'+esc(wp.pay_label)+'</b><br>'+
        'Kur mokėti: <b>'+esc(wp.pay_email)+'</b><br>'+
        'Suma: <b>'+fmt(wp.total)+' €</b><br>'+
        '<a href="mailto:'+esc(wp.winner_contact)+'?subject='+subj+'&body='+body+'" style="display:inline-block;margin-top:8px;color:#7dffa8;font-weight:700;">Siųsti instrukcijas laimėtojui</a>'+
        '</div>';
    }
    els.liveBox.innerHTML =
      '<div class="live-row">'+img+
      '<div class="live-info"><div class="live-title">#'+lot.lot_number+' '+esc(lot.title)+'</div><div class="live-meta">'+statusTxt+'</div></div>'+
      '<button class="btn-danger" id="endBtn">Baigti dabar</button></div>'+payBlock;
    document.getElementById('endBtn').onclick=function(){
      if(confirm('Baigti šį lotą dabar?')) fetch('/api/admin/end_lot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass})}).then(refresh);
    };
  }

  els.queueCount.textContent = d.queue.length;
  if(!d.queue.length){
    els.queueBox.innerHTML = '<div class="empty-note">Eilėje nieko nėra.</div>';
  } else {
    var h='';
    d.queue.forEach(function(q, i){
      var img = q.photo_file ? '<img src="/photos/'+q.photo_file+'">' : '<img>';
      h += '<div class="q-row">'+img+
        '<div class="q-info"><b>'+esc(q.title)+'</b>nuo '+fmt(q.starting_price)+' €</div>'+
        '<div class="q-actions">'+
          '<button data-up="'+q.id+'" '+(i===0?'disabled':'')+'>↑</button>'+
          '<button data-down="'+q.id+'" '+(i===d.queue.length-1?'disabled':'')+'>↓</button>'+
          '<button data-del="'+q.id+'" class="del">✕</button>'+
        '</div></div>';
    });
    els.queueBox.innerHTML = h;
    els.queueBox.querySelectorAll('[data-up]').forEach(function(b){ b.onclick=function(){ queueAction('/api/admin/queue/move', parseInt(b.getAttribute('data-up')), {dir:'up'}); }; });
    els.queueBox.querySelectorAll('[data-down]').forEach(function(b){ b.onclick=function(){ queueAction('/api/admin/queue/move', parseInt(b.getAttribute('data-down')), {dir:'down'}); }; });
    els.queueBox.querySelectorAll('[data-del]').forEach(function(b){ b.onclick=function(){ if(confirm('Pašalinti šią prekę iš eilės?')) queueAction('/api/admin/queue/delete', parseInt(b.getAttribute('data-del'))); }; });
  }

  if(!d.past_lots.length){
    els.pastBox.innerHTML = '<div class="empty-note">Kol kas nieko neparduota.</div>';
  } else {
    var h2='';
    d.past_lots.forEach(function(l){
      var extra = '';
      if(l.current_bidder && l.pay_label){
        extra = '<div style="font-size:12px;color:#9ad;margin-top:4px;">'+esc(l.pay_label)+' · '+esc(l.winner_contact||'')+' · mokėti į '+esc(l.pay_email||'')+'</div>';
      }
      h2 += '<div class="past-row"><span>#'+l.lot_number+' '+esc(l.title)+'</span><span>'+(l.current_bidder?('<b>'+fmt(l.current_price)+' €</b> · '+esc(l.current_bidder)):'be pasiūlymų')+'</span>'+extra+'</div>';
    });
    els.pastBox.innerHTML = h2;
  }

  var regs = d.registrations || [];
  els.regCount.textContent = d.registration_count != null ? d.registration_count : regs.length;
  var doms = d.email_domains || [];
  if(!doms.length){
    els.domBox.innerHTML = '';
  } else {
    els.domBox.innerHTML = doms.map(function(x){
      return '<span class="dom-pill"><b>'+esc(x.count)+'</b> · '+esc(x.domain)+'</span>';
    }).join('');
  }
  if(!regs.length){
    els.regBox.innerHTML = '<div class="empty-note">Kol kas nėra registracijų.</div>';
  } else {
    var rh = '<table class="reg-table"><thead><tr><th>Laikas</th><th>Vardas</th><th>Slapyvardis</th><th>El. paštas</th><th>Tel.</th><th>Domenas</th><th>Mokėjimas</th></tr></thead><tbody>';
    regs.forEach(function(p){
      rh += '<tr><td>'+esc(p.at_lt||'')+'</td><td>'+esc(p.name||'')+'</td><td>'+esc(p.nickname||'')+'</td><td>'+esc(p.contact||'')+'</td><td>'+esc(p.phone||'')+'</td><td><b>'+esc(p.email_domain||'')+'</b></td><td>'+esc(p.pay_method||'')+'</td></tr>';
    });
    rh += '</tbody></table>';
    els.regBox.innerHTML = rh;
  }
}

function refresh(){
  if(!pass) return;
  fetch('/api/admin/dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass})})
    .then(function(r){ if(r.status===403){ throw new Error('bad'); } return r.json(); })
    .then(renderDash)
    .catch(function(){ localStorage.removeItem('admin_pass'); pass=''; showLogin('Sesija baigėsi, prisijunk iš naujo.'); });
}

if(pass){ showDash(); } else { showLogin(''); }
setInterval(function(){ if(pass) refresh(); }, 4000);
</script>
</body></html>"""


@app.get("/googleb05d62245ed37651.html")
def google_site_verification():
    # Google Search Console HTML failo patvirtinimas
    return Response(
        content="google-site-verification: googleb05d62245ed37651.html",
        media_type="text/html; charset=utf-8",
    )


@app.get("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        "Disallow: /demo\n"
        "Sitemap: https://penktadienioaukcionas.lt/sitemap.xml\n"
    )
    return Response(content=body, media_type="text/plain; charset=utf-8")


# IndexNow — Bing, Yandex ir kt. paieškos (Google reikalauja Search Console)
INDEXNOW_KEY = (os.environ.get("INDEXNOW_KEY") or "6b321049f7347f0651001099b9ff397d").strip()


@app.get(f"/{INDEXNOW_KEY}.txt")
def indexnow_key_file():
    return Response(content=INDEXNOW_KEY + "\n", media_type="text/plain; charset=utf-8")


@app.get("/sitemap.xml")
def sitemap_xml():
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        "    <loc>https://penktadienioaukcionas.lt/</loc>\n"
        "    <changefreq>daily</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "  <url>\n"
        "    <loc>https://www.penktadienioaukcionas.lt/</loc>\n"
        "    <changefreq>daily</changefreq>\n"
        "    <priority>0.9</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    return Response(content=body, media_type="application/xml; charset=utf-8")


@app.get("/api/build")
def api_build():
    """Lankytojo naršyklė tikrina ar yra nauja versija — be Ctrl+F5."""
    return Response(
        content=json.dumps({"id": BUILD_ID, "ok": True}),
        media_type="application/json; charset=utf-8",
        headers=dict(NO_CACHE_HEADERS),
    )


@app.get("/", response_class=HTMLResponse)
def index():
    html = INDEX_HTML.replace("__BUILD_ID__", BUILD_ID)
    html = html.replace(
        "__DANCER_URLS_JSON__",
        json.dumps(DANCER_URLS, ensure_ascii=False, separators=(",", ":")),
    )
    stage_on = get_vilkas_stage_on()
    html = html.replace("__BODY_CLASS__", "stage-on" if stage_on else "cover-mode")
    html = html.replace("__DISCO_CLASS__", "" if stage_on else "on")
    html = html.replace("__WOLF_POP_CLASS__", "show alive" if stage_on else "")
    headers = dict(NO_CACHE_HEADERS)
    headers["Permissions-Policy"] = "autoplay=*"
    headers["Feature-Policy"] = "autoplay *"
    return HTMLResponse(html, headers=headers)


@app.get("/admin", response_class=HTMLResponse)
def admin():
    return HTMLResponse(
        ADMIN_HTML,
        headers=dict(NO_CACHE_HEADERS),
    )


@app.post("/api/admin/registracijos")
async def api_admin_registracijos(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        raise HTTPException(403, "neteisingas slaptazodis")
    include_demo = bool(body.get("include_demo"))
    con = db()
    people = _list_registrations(con, include_demo=include_demo)
    con.close()
    domains: dict[str, int] = {}
    for person in people:
        d = person.get("email_domain") or "(nėra)"
        domains[d] = domains.get(d, 0) + 1
    _rebuild_admin_registracijos_files()
    return {
        "ok": True,
        "count": len(people),
        "people": people,
        "email_domains": [{"domain": k, "count": v} for k, v in sorted(domains.items(), key=lambda x: (-x[1], x[0]))],
        "folder": str(ADMIN_REG_DIR),
    }


@app.get("/admin/registracijos")
def admin_registracijos_redirect():
    return RedirectResponse(url="/admin", status_code=302)
