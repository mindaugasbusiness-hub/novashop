#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Saugus vietinis tiltas n8n -> fiksuotos CLINE automatizavimo komandos."""
import json
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(r"C:\Users\M\CLINE")
SECRET_FILE = ROOT / "tools" / "automation-secret.txt"
LOG = ROOT / "AUTOMATION_API_LOG.txt"
PYTHON = r"C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
COLLECT = ROOT / "tools" / "surinkti-viska.py"
ENSURE = ROOT / "tools" / "zveris-ensure.ps1"
SECRET = SECRET_FILE.read_text(encoding="utf-8").strip()
LOCK = threading.Lock()
LOCK_STATE = {"held_since": 0.0}
MAX_LOCK_SECONDS = 240
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def log(text):
    line = time.strftime("[%Y-%m-%d %H:%M:%S] ") + text + "\n"
    try:
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass


def run_fixed(action, timeout=90):
    if action == "collect":
        cmd = [PYTHON, "-X", "utf8", str(COLLECT)]
    elif action == "ensure":
        cmd = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ENSURE)]
    else:
        raise ValueError("Nežinomas veiksmas")
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "out.txt"
        err_path = Path(tmp) / "err.txt"
        with out_path.open("wb") as out_handle, err_path.open("wb") as err_handle:
            child = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdin=subprocess.DEVNULL,
                stdout=out_handle,
                stderr=err_handle,
                creationflags=CREATE_NO_WINDOW,
            )
            try:
                exit_code = child.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = 124
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
        text = ""
        for path in (out_path, err_path):
            try:
                text += path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    text = text.strip()
    if len(text) > 4000:
        text = text[-4000:]
    if timed_out:
        text += f"\nVIRŠYTA {timeout} s riba, procesas sustabdytas."
    log(f"{action} exit={exit_code} secs={time.time()-started:.1f} {text[:400]}")
    return {"action": action, "exit_code": exit_code, "timed_out": timed_out, "output": text}


def acquire_lock():
    if LOCK.acquire(blocking=False):
        LOCK_STATE["held_since"] = time.time()
        return True
    held = time.time() - (LOCK_STATE.get("held_since") or 0)
    if held > MAX_LOCK_SECONDS:
        log(f"UZRAKTAS laikytas {held:.0f} s - atlaisvinamas priverstinai")
        try:
            LOCK.release()
        except RuntimeError:
            pass
        if LOCK.acquire(blocking=False):
            LOCK_STATE["held_since"] = time.time()
            return True
    return False


def release_lock():
    LOCK_STATE["held_since"] = 0.0
    try:
        LOCK.release()
    except RuntimeError:
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = "ClineAutomation/1.0"

    def log_message(self, fmt, *args):
        pass

    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        return self.headers.get("X-Automation-Key", "") == SECRET

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "service": "cline-automation", "actions": ["ensure", "collect", "run"]})
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self.authorized():
            self.send_json(401, {"error": "Unauthorized"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 65536:
            self.send_json(413, {"error": "Request too large"})
            return
        if length:
            self.rfile.read(length)
        action = self.path.strip("/")
        if action not in ("ensure", "collect", "run"):
            self.send_json(404, {"error": "Not found"})
            return
        try:
            if not acquire_lock():
                self.send_json(409, {"error": "Automatika jau vykdoma"})
                return
            try:
                steps = ["ensure", "collect"] if action == "run" else [action]
                results = [run_fixed(step) for step in steps]
            finally:
                release_lock()
            self.send_json(200, {"ok": all(r["exit_code"] == 0 for r in results), "results": results})
        except Exception as exc:
            log(f"{action} ERROR {exc}")
            self.send_json(500, {"ok": False, "error": str(exc)})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8792), Handler).serve_forever()
