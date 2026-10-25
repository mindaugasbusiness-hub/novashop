#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surenka VISKAS istorija ir vietines Cline sesijas i viena naujausia faila."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Users\M\CLINE")
VISKAS = BASE / "VISKAS"
OUT_FULL = VISKAS / "00_VISKAS_PILNA_ISTORIJA.md"
OUT_SHORT = VISKAS / "00_SKAITYK_NAUJAUSIA.md"
STATE = VISKAS / "00_SURINKIMO_BUSENA.json"
CLOUD = VISKAS / "SESIJA_2026-10-25_CLOUD.md"
SESSION_ROOTS = [
    Path(r"C:\Users\M\.cline\data\sessions"),
    Path(r"C:\Users\M\AppData\Roaming\Code\User\globalStorage\saoudrizwan.claude-dev\tasks"),
    Path(r"C:\Users\M\AppData\Roaming\Cursor\User\globalStorage\saoudrizwan.claude-dev\tasks"),
]
CORE = [
    VISKAS / "VISKAS_VISKAS.md",
    BASE / "00_START_HERE.md",
    BASE / "02_DIENORASTIS.md",
    BASE / "04_TODO.md",
    BASE / "09_PAKEITIMAI.md",
    VISKAS / "02_ATLIKTI_DARBAI.md",
    VISKAS / "05_TODO.md",
    VISKAS / "06_DABARTINE_BUSENA.md",
]
SIGNATURE = hashlib.sha256()
SOURCES = []


def read_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return f"[NEPAVYKO PERSKAITYTI: {exc}]"
    SIGNATURE.update(str(path).encode())
    SIGNATURE.update(str(path.stat().st_mtime_ns).encode())
    SIGNATURE.update(text.encode("utf-8", errors="replace"))
    SOURCES.append(str(path))
    return text.replace("\r\n", "\n")


def value_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(value_text(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def message_text(message: dict) -> str:
    parts = []
    for item in message.get("content") or []:
        if not isinstance(item, dict):
            parts.append(str(item))
            continue
        typ = item.get("type")
        if typ == "thinking":
            continue
        if typ == "text":
            parts.append(str(item.get("text") or ""))
        elif typ == "tool_use":
            args = json.dumps(item.get("input") or {}, ensure_ascii=False, default=str)
            parts.append(f"[TOOL {item.get('name') or '?'}] {args[:6000]}")
        elif typ == "tool_result":
            body = value_text(item.get("content"))
            parts.append(f"[REZULTATAS {item.get('name') or '?'}] {body[:8000]}")
        else:
            body = value_text(item.get("text") or item.get("content") or "")
            if body:
                parts.append(body)
    return "\n".join(p for p in parts if p.strip())


def collect_sessions():
    sessions = []
    seen = set()
    for root in SESSION_ROOTS:
        if not root.is_dir():
            continue
        for folder in root.iterdir():
            if not folder.is_dir():
                continue
            candidates = list(folder.glob("*.messages.json"))
            if not candidates:
                continue
            msg_path = max(candidates, key=lambda p: p.stat().st_mtime)
            if msg_path in seen:
                continue
            seen.add(msg_path)
            meta_path = folder / (folder.name + ".json")
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8-sig", errors="replace")) if meta_path.is_file() else {}
            except Exception:
                meta = {}
            try:
                raw = json.loads(msg_path.read_text(encoding="utf-8-sig", errors="replace"))
                messages = raw.get("messages") or (raw if isinstance(raw, list) else [])
            except Exception as exc:
                sessions.append({"folder": folder, "meta": meta, "error": str(exc), "messages": []})
                continue
            title = ((meta.get("metadata") or {}).get("title") or meta.get("prompt") or folder.name)
            sessions.append({"folder": folder, "meta": meta, "title": str(title), "messages": messages, "msg_path": msg_path})
    sessions.sort(key=lambda s: str(s["meta"].get("started_at") or s["folder"].stat().st_mtime), reverse=True)
    return sessions


def render_session(session: dict) -> str:
    meta = session.get("meta") or {}
    lines = [
        f"\n## SESIJA: {session.get('title')}",
        f"- Katalogas: `{session['folder']}`",
        f"- Pradžia: {meta.get('started_at','?')} | modelis: {meta.get('model','?')} | statusas: {meta.get('status','?')}",
    ]
    if session.get("error"):
        lines.append("- KLAIDA: " + session["error"])
        return "\n".join(lines)
    for m in session.get("messages") or []:
        body = message_text(m).strip()
        if not body:
            continue
        try:
            when = datetime.fromtimestamp(int(m.get("ts")) / 1000).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            when = "?"
        lines.append(f"\n### {when} · {(m.get('role') or '?').upper()}\n{body}")
    return "\n".join(lines)



def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    core_parts = []
    for path in CORE:
        core_parts.append(f"\n\n# ==== {path} ====\n{read_text(path)}")
    sessions = collect_sessions()
    session_parts = []
    for session in sessions:
        session_parts.append(read_text(session["msg_path"]))
        session_parts.append(render_session(session))
    cloud = read_text(CLOUD) if CLOUD.is_file() else "[NĖRA ŠIOS DIENOS CLOUD SESIJOS SANTRAUKOS]"
    signature = SIGNATURE.hexdigest()
    previous = ""
    try:
        if STATE.is_file():
            previous = json.loads(STATE.read_text(encoding="utf-8")).get("signature", "")
    except Exception:
        previous = ""
    if previous == signature and OUT_FULL.is_file() and OUT_SHORT.is_file():
        print("VISKAS: pakitimų nėra, failai jau naujausi.")
        return 0
    full = [
        "# VISKAS — PILNA NAUJAUSIA ISTORIJA",
        f"\nSugeneruota: **{now}**  ",
        f"Šaltinių: **{len(SOURCES)}** · vietinių Cline sesijų: **{len(sessions)}**",
        "\n> Šis failas sugeneruotas automatiškai. Jame VISKAS dokumentai ir visos rastos vietinės Cline sesijos.",
        "\n\n# ŠIOS DIENOS CLOUD SESIJOS SANTRAUKA\n" + cloud,
        *core_parts,
        "\n\n# ==== VISOS VIETINĖS CLINE SESIJOS (naujausios viršuje) ====",
        *session_parts,
    ]
    short = [
        "# NAUJAUSIA — SKAITYK PIRMA",
        f"\nSugeneruota: **{now}**",
        "\nNaujam DI duok:",
        "```",
        r"Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.",
        "```",
        "\n## PILNA ISTORIJA",
        f"`{OUT_FULL}` — {len(sessions)} Cline sesijos, VISKAS dokumentai ir visi darbai.",
        "\n## DABARTINĖ BŪSENA",
        read_text(VISKAS / "06_DABARTINE_BUSENA.md"),
        "\n## VISKAS VIENAME FAILE",
        read_text(VISKAS / "VISKAS_VISKAS.md"),
        "\n## PASKUTINIS DIENORAŠTIS",
        "\n".join(read_text(BASE / "02_DIENORASTIS.md").splitlines()[:180]),
    ]
    temp_full = OUT_FULL.with_suffix(".tmp")
    temp_short = OUT_SHORT.with_suffix(".tmp")
    temp_full.write_text("\n".join(full), encoding="utf-8")
    temp_short.write_text("\n".join(short), encoding="utf-8")
    os.replace(temp_full, OUT_FULL)
    os.replace(temp_short, OUT_SHORT)
    STATE.write_text(json.dumps({
        "signature": signature,
        "generated": now,
        "sources": len(SOURCES),
        "sessions": len(sessions),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"VISKAS SURINKTA: {OUT_FULL} ({OUT_FULL.stat().st_size} B), sesijos={len(sessions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
