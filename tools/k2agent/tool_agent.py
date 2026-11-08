# -*- coding: utf-8 -*-
"""K2 mini-agentas su irankiais (Groq gpt-oss-120b).
SAUGUS REZIMAS: skaitymas visada; rasymas ir PowerShell - TIK su --leisti-keitimus."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\viliu\CLINE")
OUT = Path(r"C:\Users\viliu\Desktop\n8n_atsakymai")
MODEL = "openai/gpt-oss-120b"
DRAUDZIAMA = ("remove-item", " del ", "rd /s", "rmdir", "format ", "shutdown", "restart-computer",
              "stop-computer", "diskpart", "mkfs", "cipher /w", "reg delete", "vssadmin")

SYSTEM = (
    "Tu esi K2 kompiuterio prieziuros agentas, dirbi su Windows. Naudok irankius duomenims rinkti. "
    "Atsakyk lietuviskai, trumpai ir konkreciai. Jei irankis parase klaida - pabandyk kita kelia, "
    "bet ne daugiau 2 kartu. NIEKO NETRINK. Jei uzduociai reikia keitimu, o tau neleista - "
    "parasyk, kad reikia leidimo."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_dir", "description": "Failu ir aplanku sarasas",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Perskaityti tekstini faila",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "lines": {"type": "integer"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_log", "description": "Paskutines logo eilutes",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "lines": {"type": "integer"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "check_port", "description": "Ar portas klauso (127.0.0.1)",
        "parameters": {"type": "object", "properties": {
            "port": {"type": "integer"}}, "required": ["port"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "IRASYTI faila (reikia leidimo keitimams)",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "run_powershell", "description": "PowerShell komanda (reikia leidimo; be trynimo)",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}}, "required": ["command"]}}},
]


def load_env():
    env = ROOT / "ai-stack" / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def groq(messages, timeout=180):
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("nera GROQ_API_KEY")
    payload = {"model": os.environ.get("AGENT_MODEL", MODEL), "messages": messages,
               "temperature": 0.2, "max_tokens": 1500, "tools": TOOLS, "tool_choice": "auto"}
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def kelias(p):
    try:
        return Path(os.path.expandvars(str(p)))
    except Exception:
        return Path(str(p))


def run_tool(name, a, leisti):
    try:
        if name == "list_dir":
            p = kelias(a.get("path", ""))
            if not p.exists():
                return "NERA: %s" % p
            eil = [("[DIR] " if x.is_dir() else "      ") + x.name for x in sorted(p.iterdir())[:80]]
            return "\n".join(eil) or "(tuscias)"
        if name == "read_file":
            p, n = kelias(a.get("path", "")), int(a.get("lines") or 100)
            if not p.is_file():
                return "NERA failo: %s" % p
            return "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:n])[:6000]
        if name == "read_log":
            p, n = kelias(a.get("path", "")), int(a.get("lines") or 40)
            if not p.is_file():
                return "NERA: %s" % p
            return "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])[:6000]
        if name == "check_port":
            import socket
            port = int(a.get("port") or 0)
            s = socket.socket()
            s.settimeout(2)
            ok = s.connect_ex(("127.0.0.1", port)) == 0
            s.close()
            return ("KLAUSO" if ok else "NEKLAUSO") + " :%d" % port
        if name in ("write_file", "run_powershell") and not leisti:
            return "NEGALIMA: keitimai neleisti (reikia leidimo)"
        if name == "write_file":
            p = kelias(a.get("path", ""))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(a.get("content") or ""), encoding="utf-8")
            return "IRASYTA: %s (%d B)" % (p, p.stat().st_size)
        if name == "run_powershell":
            komanda = str(a.get("command") or "")
            low = " " + komanda.lower() + " "
            if any(d in low for d in DRAUDZIAMA):
                return "BLOKUOTA: komandoje yra draudziama operacija"
            r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-Command", komanda], capture_output=True, text=True,
                               timeout=90, encoding="utf-8", errors="replace")
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            return (out or "(be isvesties)")[:5000] + "\n[rc=%s]" % r.returncode
        return "Nezymomas irankis: %s" % name
    except Exception as e:  # noqa: BLE001
        return "IRANKIO KLAIDA: %s: %s" % (type(e).__name__, str(e)[:200])


def main():
    load_env()
    args = sys.argv[1:]
    leisti = "--leisti-keitimus" in args
    task = " ".join(x for x in args if not x.startswith("--")).strip()
    if not task:
        print(json.dumps({"ok": False, "klaida": "tuscia uzduotis"}, ensure_ascii=False))
        return 2
    veiksmai = []
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    atsakymas = ""
    try:
        for _ in range(8):
            d = groq(messages)
            msg = d["choices"][0]["message"]
            messages.append(msg)
            calls = msg.get("tool_calls") or []
            if not calls:
                atsakymas = (msg.get("content") or "").strip()
                break
            for c in calls:
                fn = c.get("function", {})
                name = fn.get("name", "")
                try:
                    a = json.loads(fn.get("arguments") or "{}")
                except ValueError:
                    a = {}
                res = run_tool(name, a, leisti)
                veiksmai.append("%s(%s) -> %s" % (name, json.dumps(a, ensure_ascii=False)[:100], res[:100]))
                messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": res[:5000]})
    except urllib.error.HTTPError as e:
        print(json.dumps({"ok": False, "klaida": "groq HTTP %s" % e.code}, ensure_ascii=False))
        return 1
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "klaida": str(e)[:300]}, ensure_ascii=False))
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / ("agentas_%s.md" % time.strftime("%Y-%m-%d_%H-%M-%S"))
    f.write_text("# Mini-agentas (120b + irankiai)\n\nUzduotis: %s\n\n## Atsakymas\n%s\n\n## Veiksmai\n%s\n"
                 % (task, atsakymas, "\n".join("- " + v for v in veiksmai) or "(irankiu nenaudojo)"),
                 encoding="utf-8")
    print(json.dumps({"ok": True, "failas": str(f), "text": atsakymas, "veiksmai": veiksmai,
                      "finishReason": "stop"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
